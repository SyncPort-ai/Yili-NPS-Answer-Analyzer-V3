# coding:utf-8

import pandas as pd
import numpy as np
import time
import re
import requests

from llm import AzureEmbedding, AzureChat, AzureChatApp
from prompts import prompt_create, create_prompt_title
from cluster import text_cluster


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

def result_process(model, df, question, theme, emotion, start_num, step):
    """
    取[start_num: start_num + step]的非空回答拼成一个请求，
    返回的结果按照分割符@拆分到对应答案
    每个答案的不同维度用；拆分，从（评价维度，原因）中提取dim和opinion，与对应答案一同append
    """
    
    chunk = df.iloc[start_num: start_num + step,:] # 取50条
    chunk = chunk[(chunk.clean!='')&(chunk.clean.isna()==0)][['clean','mark']].reset_index()
    if len(chunk)==0:
        print('无有效数据，不打标')
        return pd.DataFrame()
    
    answer = ''
    for ind,row in chunk.iterrows():
        answer += f"{ind+1}. {row['clean']}\n"


    responses = model.chat(prompt_create(question,theme,emotion,answer))  # 调用

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

# 批次拆分，调用大模型打标
def sentiment_triplet_extraction(model, df, question, theme, emotion):

    #初始化
    start_num = 0
    step_default1, step_default2, step_default3 = 30, 10, 5
    result = pd.DataFrame(columns=['mark', 'aspect', 'opinion'])
    result_sub = pd.DataFrame()
    
    #如果50个跑不对跑30个，30个跑不对跑10个，10个再给一次机会，再不行就空着
    while start_num < len(df):
        try:
            step = 50
            result_sub = result_process(model, df, question,theme,emotion,start_num,step)
            print(f"成功处理{start_num}~{start_num+step}")
        except Exception as e:
            try:
                step = step_default1
                result_sub = result_process(model,df, question,theme,emotion,start_num,step)
                print(f"成功处理{start_num}~{start_num+step}")
            except Exception as e:
                try:
                    step = step_default2
                    result_sub = result_process(model,df, question,theme,emotion,start_num,step)
                    print(f"成功处理{start_num}~{start_num+step}")
                except Exception as e:
                    try:
                        step=step_default2
                        result_sub = result_process(model,df, question,theme,emotion,start_num,step)
                        print(f"成功处理{start_num}~{start_num+step}")
                    except Exception as e:
                        try:
                            step=step_default3
                            result_sub = result_process(model,df, question,theme,emotion,start_num,step)
                            print(f"成功处理{start_num}~{start_num+step}")
                        except Exception as e:
                            try:
                                step=step_default3
                                result_sub = result_process(model,df, question,theme,emotion,start_num,step)
                                print(f"成功处理{start_num}~{start_num+step}")
                            except Exception as e:
                                step = step_default3
                                print(f"处理 {start_num}~{start_num+step} 时出错")
                                result_sub = pd.DataFrame({
                                    'mark': df.iloc[start_num:start_num+step_default3]['mark'],
                                    'aspect': '未知',
                                    'opinion': '未知'
                                    })
                                print(e)
        
        start_num += step
        result = pd.concat([result,result_sub], ignore_index=True)
    return result

# 打标函数
def text_labelling(model, df, question, theme, emotion):
# def text_labelling(model, df, theme, emotion):
    start_time = time.time()
    try:
        temp_result = sentiment_triplet_extraction(model, df, question, theme, emotion)
        df1 = df.merge(temp_result, on='mark', how='left')
        end_time = time.time()
        print(f"处理{len(df)}条耗时{end_time-start_time}秒，平均{(end_time-start_time)/len(df)*10}秒/10条")
        return df1
    except requests.RequestException as e:
        raise ModelCallError(f"调用语言模型时出错: {str(e)}", "labeling")
    except Exception as e:
        raise LabelingError(f"标注过程中出错: {str(e)}")

def auto_analysis(question,theme,emotion,data,mode):
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
        df = text_labelling(model, data, question, theme, emotion)

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
        category_title = {i: [] for i in range(best_n_clusters)}
        for i, label in enumerate(cluster_labels):  
            category[label].append(texts[i])
            category_index[label].append(i)
        for i in range(best_n_clusters): 
            answer_list = category[i]
            retry_count = 0
            max_retries = 3
            title = "标题生成异常"
            
            while retry_count < max_retries:
                try:
                    title = model.chat(create_prompt_title(theme, emotion, answer_list))
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        print(f"生成标题失败，已重试{max_retries}次: {str(e)}")
                    else:
                        print(f"生成标题失败，正在进行第{retry_count}次重试: {str(e)}")
                        time.sleep(1)  # 每次重试等待1秒
            print(f"主题{i}：{title}：{len(answer_list)}")
            category_title[i] = title

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
    

