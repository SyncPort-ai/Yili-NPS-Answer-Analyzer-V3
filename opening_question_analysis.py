# coding:utf-8

import pandas as pd
import numpy as np
import time
import re
import requests

from llm import AzureEmbedding, AzureChat, AzureChatApp
from prompts import prompt_create, create_prompt_title
from cluster import text_cluster

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial


class ModelCallError(Exception):
    """Raised when there's an error calling the large language model"""
    def __init__(self, message, stage):
        self.message = message
        self.stage = stage
        super().__init__(self.message)

class LabelingError(Exception):
    """Raised when there's an error during the labeling process"""
    pass

class EmbeddingError(Exception):
    """Raised when there's an error during the embedding process"""
    pass

# 数据清洗
import re
def list_process(answers):
    punctuation = f"[，。、,.;；：:/]"
    nonsence=f"(没有|无|追问|无追问|无已|已)"
    
    answer_clean=[]
    for s in answers:
        s = s.replace(" ","").replace("——","；").replace("\\","；")
        
        s = s.replace("（已追问）","").replace("（无追问）","")
        s = s.replace("(已追问)","").replace("(无追问)","")
        s = s.replace("已追问","").replace("无追问","")
        
        s = re.sub(rf'\d{punctuation}', '；', s)#1、
        s = re.sub(r'(?<!\d)\d/(?!\d)','；', s)#1/
        s = re.sub(rf'{punctuation}{punctuation}', '；', s)#、

        s = re.sub(rf'\d无已', '', s)
        s = re.sub(rf'无{punctuation}*已', '', s)
        s = re.sub(rf'{punctuation}*已$', '', s)
        s = s.replace('无已','')
        
        s = re.sub(rf'{punctuation}+{nonsence}+{punctuation}', '', s)
        s = re.sub(rf'{punctuation}+{nonsence}$', '', s)
        s = re.sub(rf'\d{nonsence}$', '', s)
        
        if s.startswith('；'): s=s[1:] 
            
        s = re.sub(rf'{punctuation}$', '', s)
        s = re.sub(rf'^\d$', '', s)
        
        s = re.sub(rf'{nonsence}$', '', s)    

        answer_clean.append(s)

    return answer_clean

async def result_process(model, df, question, theme, emotion, start_num, step):
    """
    异步处理单个批次的数据
    """
    chunk = df.iloc[start_num: start_num + step,:] # 取10条
    chunk = chunk[(chunk.clean!='')&(chunk.clean.isna()==0)][['clean','mark']].reset_index()
    if len(chunk)==0:
        print('无有效数据，不打标')
        return pd.DataFrame()
    
    answer = ''
    for ind,row in chunk.iterrows():
        answer += f"{ind+1}. {row['clean']}\n"

    # 如果 model.chat 是同步的，使用 loop.run_in_executor 将其转换为异步
    loop = asyncio.get_event_loop()
    responses = await loop.run_in_executor(None, model.chat, prompt_create(question,theme,emotion,answer))

    responses = re.sub(r'\b\d+\.', '@', responses).replace(" ","").replace("\n","")    
    responses = responses.split('@')[1:]  # 结果拆分

    if len(responses)==len(chunk): # 输入数与结果数相同
        result_sub = pd.DataFrame(columns=['mark', 'aspect', 'opinion'])
        for index,response in enumerate(responses): 
            parts = response.strip("（）").split('）|（') 
            for part in parts:
                if len(part)>0:
                    aspect, opinion= part.split('，',1) 
                    result_sub.loc[len(result_sub)]=[chunk.loc[index,'mark'],aspect,opinion]
    else:
        print(responses)
        raise ValueError(f"处理 {step} 条数据时出错") 
        
    return result_sub.drop_duplicates()


async def process_batch_with_retry(model, df, question, theme, emotion, start_num, step, max_retries=10):
    """处理单个批次，带重试机制"""
    for attempt in range(max_retries):
        try:
            result = await result_process(model, df, question, theme, emotion, start_num, step)
            print(f"成功处理{start_num}~{start_num+step}")
            return result
        except Exception as e:
            if attempt == max_retries - 1:  # 最后一次尝试也失败
                print(f"处理 {start_num}~{start_num+step} 时出错，已重试{max_retries}次")
                return pd.DataFrame({
                    'mark': df.iloc[start_num:start_num+step]['mark'],
                    'aspect': '未知',
                    'opinion': '未知'
                })
            wait_time = min(2 ** attempt, 8)  # 指数退避，最大等待60秒
            print(f"处理 {start_num}~{start_num+step} 时出错，{wait_time}秒后进行第{attempt+1}次重试")
            await asyncio.sleep(wait_time)


async def sentiment_triplet_extraction(model, df, question, theme, emotion):
    """使用异步并发处理数据批次"""
    start_time = time.time()
    
    # 计算批次
    batch_size = 20
    total_batches = (len(df) + batch_size - 1) // batch_size
    
    # 创建信号量来限制并发数
    semaphore = asyncio.Semaphore(4)  # 最大并发数为5
    
    async def process_with_semaphore(batch_start):
        async with semaphore:
            # 获取当前批次的数据
            batch_end = min(batch_start + batch_size, len(df))
            batch_df = df.iloc[batch_start:batch_end].copy()
            
            # 处理当前批次
            result = await process_batch_with_retry(
                model, df, question, theme, emotion, 
                batch_start, batch_size
            )
            
            # 直接与原始数据合并
            if not result.empty:
                batch_df = batch_df.merge(result, on='mark', how='left')
            else:
                batch_df['aspect'] = '未知'
                batch_df['opinion'] = '未知'
            
            return batch_df
    
    # 创建所有任务
    tasks = [process_with_semaphore(i * batch_size) for i in range(total_batches)]
    
    # 并发执行所有任务
    results = await asyncio.gather(*tasks)
    
    # 合并所有结果
    final_df = pd.concat(results, ignore_index=True)
    
    end_time = time.time()
    print(f"处理{len(df)}条耗时{end_time-start_time}秒，平均{(end_time-start_time)/len(df)*10}秒/10条")
    
    return final_df

# 修改 text_labelling 函数以支持异步操作
async def text_labelling(model, df, question, theme, emotion):
    try:
        # 直接返回处理后的结果，因为合并操作已经在 sentiment_triplet_extraction 中完成
        return await sentiment_triplet_extraction(model, df, question, theme, emotion)
    except requests.RequestException as e:
        raise ModelCallError(f"调用语言模型时出错: {str(e)}", "labeling")
    except Exception as e:
        raise LabelingError(f"标注过程中出错: {str(e)}")
    

async def generate_title_with_retry(model, theme, emotion, answer_list, max_retries=3):
    """异步生成标题，带重试机制"""
    title = "标题生成异常"
    loop = asyncio.get_event_loop()
    
    for retry_count in range(max_retries):
        try:
            # 使用 run_in_executor 将同步的 model.chat 转换为异步操作
            prompt = create_prompt_title(theme, emotion, answer_list)
            title = await loop.run_in_executor(None, model.chat, prompt)
            break
        except Exception as e:
            if retry_count == max_retries - 1:
                print(f"生成标题失败，已重试{max_retries}次: {str(e)}")
            else:
                print(f"生成标题失败，正在进行第{retry_count+1}次重试: {str(e)}")
                await asyncio.sleep(1)
    return title

async def generate_titles(model, theme, emotion, category, best_n_clusters):
    """批量并发生成所有标题"""
    # 使用较小的并发数以避免API限制
    num=best_n_clusters
    semaphore = asyncio.Semaphore(4)
    
    # 预处理所有prompt
    prompts = []
    for cluster_id in range(best_n_clusters):
        answer_list = category[cluster_id]
        prompts.append((cluster_id, answer_list))
        
    async def generate_with_semaphore(cluster_id, answer_list):
        async with semaphore:
            # 现在使用异步的generate_title_with_retry
            title = await generate_title_with_retry(model, theme, emotion, answer_list)
            print(title)
            return cluster_id, title
            
    # 创建所有任务
    tasks = [generate_with_semaphore(cluster_id, answer_list) 
             for cluster_id, answer_list in prompts]
    
    # gather并发执行
    results = await asyncio.gather(*tasks)
    
    # 将结果转换为字典
    category_title = {cluster_id: title for cluster_id, title in results}
    return category_title


async def auto_analysis(question,theme,emotion,data,mode):
    try:
        # 清洗
        print('完成数据处理')
        clean_answer = list_process(data['origion'].tolist())
        data['clean'] = clean_answer

        # 保存原始的 ids
        data['ids'] = data['mark']

        # 生成新的 mark 列
        data['mark'] = range(len(data))

        print('完成数据清洗')
        print(f"输入数据量：{data.shape}")
        
        # 打标
        if mode == 'uat':
            model = AzureChat()
        else:
            model = AzureChatApp()

        print("\n请等待打标...")
        df = await text_labelling(model, data, question, theme, emotion)

        print(f"打标数据量：{df['mark'].nunique()}, 标签数：{df.shape}")

        # 打标结果处理
        df_nonsense = df[df.opinion.isna()].copy()
        df_unknown = df[df.opinion == '未知'].copy()
        for col in ['aspect', 'opinion', 'aspect_opinion', 'topic']:
            if df_nonsense.empty:
                df_nonsense[col] = pd.Series(dtype='object')# 如果为空，创建这些列但不赋值
            else:
                df_nonsense.loc[:, col] = '无意义'# 如果不为空，进行赋值
                df_nonsense.loc[:, 'topic'] = ''# 如果不为空，进行赋值

        for col in ['aspect_opinion', 'topic']:
            if df_unknown.empty:
                df_unknown[col] = pd.Series(dtype='object')
            else:
                df_unknown.loc[:, col] = '未知'
                df_unknown.loc[:, 'topic'] = ''

        

        df = df[(df.opinion.isna()==0) & (df.opinion != '未知')].reset_index(drop=True)

        print(f"有效：{df.shape[0]}，无意义:{df_nonsense.shape[0]}，未知:{df_unknown.shape[0]}")

        df['aspect_opinion'] = df.apply(lambda x: f"{x['aspect']}_{x['opinion']}", axis=1)
        texts = df['aspect_opinion'].tolist()
        
        if not texts:
            print("\n无有效文本，跳过嵌入和聚类")
            result = pd.concat([df_nonsense, df_unknown], ignore_index=True)

            print(f"打标数据量：{result['mark'].nunique()}, 标签数：{result.shape}\n")

            result = result[['origion', 'ids', 'clean', 'aspect', 'opinion', 'aspect_opinion', 'topic']]

            return result
        
        unique_texts = list(set(texts))
        n_unique_texts = len(unique_texts)

        print(f"有效非重复数据：{unique_texts}")
        print(f"有效非重复数据量：{n_unique_texts}")

        if n_unique_texts<3:
            print("\n有效非重复数据少于3，跳过嵌入和聚类")
            n_samples = len(texts)
            best_n_clusters = 1
            cluster_labels = np.zeros(n_samples, dtype=int)
        else:
            # 向量化
            print("\n请等待嵌入...")
            embedding = AzureEmbedding()
            try:
                embeddings = np.array(embedding.embedding(texts))
            except Exception as e:
                print(f"嵌入过程中出错: {str(e)}")
                raise EmbeddingError(f"嵌入过程中出错: {str(e)}")
            
            # 确定聚类参数
            n_samples = len(embeddings)
            min_cluster = min(int(n_samples/4)+1,20)
            if n_samples <= 40:
                cn = [2, max(min_cluster, 3)]
            else:
                cn = [6, max(min_cluster, 7)]
            best_n_clusters, cluster_labels = text_cluster(embeddings, if_reduce=False, cn=cn)# 聚类

        print("\n请等待标题生成...")
        # 聚类完成后，为每个主题收集回答原文  
        category = {i: [] for i in range(best_n_clusters)}  
        category_index = {i: [] for i in range(best_n_clusters)} 
        for i, label in enumerate(cluster_labels):  
            category[label].append(texts[i])
            category_index[label].append(i)
        
        # 并发生成标题    
        category_title = await generate_titles(model, theme, emotion, category, best_n_clusters)
        for i in range(best_n_clusters):
            print(f"主题{i}：{category_title[i]}：{len(category[i])}")

        # category = {i: [] for i in range(best_n_clusters)}  
        # category_index = {i: [] for i in range(best_n_clusters)} 
        # category_title = {i: [] for i in range(best_n_clusters)}
        # for i, label in enumerate(cluster_labels):  
        #     category[label].append(texts[i])
        #     category_index[label].append(i)
        # for i in range(best_n_clusters): 
        #     answer_list = category[i]
        #     retry_count = 0
        #     max_retries = 3
        #     title = "标题生成异常"
            
        #     while retry_count < max_retries:
        #         try:
        #             title = model.chat(create_prompt_title(theme, emotion, answer_list))
        #             break
        #         except Exception as e:
        #             retry_count += 1
        #             if retry_count == max_retries:
        #                 print(f"生成标题失败，已重试{max_retries}次: {str(e)}")
        #             else:
        #                 print(f"生成标题失败，正在进行第{retry_count}次重试: {str(e)}")
        #                 time.sleep(1)  # 每次重试等待1秒
        #     print(f"主题{i}：{title}：{len(answer_list)}")
        #     category_title[i] = title

        # 聚类主体回填
        df['topic_num'] = [label for label in cluster_labels]
        df['topic'] = [category_title[label] for label in cluster_labels]

        result = pd.concat([df, df_nonsense, df_unknown], ignore_index=True)
        print(f"打标数据量：{result['mark'].nunique()}, 标签数：{result.shape}\n")

        result = result[['origion', 'ids', 'clean', 'aspect', 'opinion', 'aspect_opinion', 'topic']]
        

        # # 输出展示
        # for label in range(best_n_clusters): 
        #     topic_answers=df[df.topic_num==label].reset_index()
        #     print(f"主题{label}：{category_title[label]}，声量{len(topic_answers)}")
        #     print('回答原文：')
        #     for i,row in topic_answers.iterrows():
        #         print(f"- {row['aspect_opinion']}（原文：{row['clean']}）")
        #     print()

        # print('主题：未知')
        # for i,row in df_unknown.iterrows():
        #     print(row['clean'])
        # print()
        # print('主题：无意义')
        # for i,row in df_nonsense.iterrows():
        #     print(row['clean'])

        return result

    except ModelCallError as e:
        print(f"模型调用错误: {e}")
        raise
    except LabelingError as e:
        print(f"标注错误: {e}")
        raise
    except EmbeddingError as e:
        print(f"嵌入错误: {e}")
        raise
    except Exception as e:
        print(f"auto_analysis 中出现意外错误: {e}")
        raise
    

