# coding:utf-8

import pandas as pd
import numpy as np
import time
import re
import requests

from llm import AzureEmbedding, AzureChat, AzureChatApp
from prompts import prompt_create,create_prompt_title
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
        #print(s)
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


def result_process(model, df,theme, emotion, start_num, step):
    """
    取[start_num: start_num + step]的非空回答拼成一个请求，
    返回的结果按照分割符@拆分到对应答案
    每个答案的不同维度用；拆分，从（评价维度，原因）中提取dim和reason，与对应答案一同append
    """
    
    chunk = df.iloc[start_num: start_num + step,:] # 取50条
    chunk = chunk[(chunk.clean!='')&(chunk.clean.isna()==0)][['clean','mark']].reset_index()
    answer = ''
    for ind,row in chunk.iterrows():
        answer += f"{ind+1}. {row['clean']}\n"


    responses = model.chat(prompt_create(theme,emotion,answer))  # 调用

    responses = re.sub(r'\b\d+\.', '@', responses).replace(" ","").replace("\n","")    
    responses = responses.split('@')[1:]  # 结果拆分

    if len(responses)==len(chunk): # 输入数与结果数相同
        result_sub = pd.DataFrame(columns=['mark', 'dimension', 'reason'])
        for index,response in enumerate(responses): 
            parts = response.strip("（）").split('）|（') 
            for part in parts:
                if len(part)>0:
                    dimension, reason= part.split('，',1) 
                    result_sub.loc[len(result_sub)]=[chunk.loc[index,'mark'],dimension,reason]
    else:
        print(responses)
        raise ValueError(f"Error processing {step} items") 
        
    return result_sub.drop_duplicates()

# 批次拆分，调用大模型打标
def sentiment_triplet_extraction(model, df,theme,emotion):
    #初始化
    start_num = 0
    step_default1, step_default2, step_default3 = 30, 10, 5
    result = pd.DataFrame(columns=['mark', 'dimension', 'reason'])
    result_sub = pd.DataFrame()
    
    #如果50个跑不对跑30个，30个跑不对跑10个，10个再给一次机会，再不行就空着
    while start_num < len(df):
        try:
            step = 50
            result_sub = result_process(model, df,theme,emotion,start_num,step)
            print(f"成功处理{start_num}~{start_num+step}")
        except Exception as e:
            try:
                step = step_default1
                result_sub = result_process(model,df,theme,emotion,start_num,step)
                print(f"成功处理{start_num}~{start_num+step}")
            except Exception as e:
                try:
                    step = step_default2
                    result_sub = result_process(model,df,theme,emotion,start_num,step)
                    print(f"成功处理{start_num}~{start_num+step}")
                except Exception as e:
                    try:
                        step=step_default2
                        result_sub = result_process(model,df,theme,emotion,start_num,step)
                        print(f"成功处理{start_num}~{start_num+step}")
                    except Exception as e:
                        try:
                            step=step_default3
                            result_sub = result_process(model,df,theme,emotion,start_num,step)
                            print(f"成功处理{start_num}~{start_num+step}")
                        except Exception as e:
                            try:
                                step=step_default3
                                result_sub = result_process(model,df,theme,emotion,start_num,step)
                                print(f"成功处理{start_num}~{start_num+step}")
                            except Exception as e:
                                step = step_default3
                                print(f"Error response {start_num}~{start_num+step}")
                                result_sub = pd.DataFrame({
                                    'mark': df.iloc[start_num:start_num+step_default3]['mark'],
                                    'dimension': '未知',
                                    'reason': '未知'
                                    })
                                print(e)
        
        start_num += step
        result = pd.concat([result,result_sub], ignore_index=True)
    return result

# 打标函数
def text_labelling(model, df, theme, emotion):
    start_time = time.time()
    try:
        temp_result = sentiment_triplet_extraction(model, df, theme, emotion)
        df1 = df.merge(temp_result, on='mark', how='left')
        end_time = time.time()
        print(f"处理{len(df)}条耗时{end_time-start_time}秒，平均{(end_time-start_time)/len(df)*10}秒/10条")
        return df1
    except requests.RequestException as e:
        raise ModelCallError(f"调用语言模型时出错: {str(e)}", "labeling")
    except Exception as e:
        raise LabelingError(f"标注过程中出错: {str(e)}")




def auto_analysis(theme,emotion,data,mode):
    # try:
        # 清洗
        clean_answer = list_process(data['origion'].tolist())
        data['clean'] = clean_answer

        # 保存原始的 ids
        data['ids'] = data['mark']

        # 生成新的 mark 列
        data['mark'] = range(len(data))

        print(f"标签数量：{data['mark'].nunique()}")
        print(f"数据量：{data.shape}")


        # 打标
        if mode == 'uat':
            model = AzureChat()
        else:
            model = AzureChatApp()

        print("Please wait for labeling...")
        df = text_labelling(model, data, theme, emotion)

        #print(df)
        print(f"标签数量：{df['mark'].nunique()}")
        print(f"数据量：{df.shape}")

        # 打标结果处理
        df_nonsense = df[df.reason == 'nonsense'].copy()
        df_unknown = df[df.reason == '未知'].copy()

        print(f"无意义结果数量:{df_nonsense.shape}")
        print(f"未知结果数量:{df_unknown.shape}")


        for col in ['dimension', 'reason', 'dim_reason', 'topic']:
            if df_nonsense.empty:
                df_nonsense[col] = pd.Series(dtype='object')
            else:
                df_nonsense.loc[:, col] = '无意义'

        if df_unknown.empty:
            # 如果为空，创建这些列但不赋值
            df_unknown['dim_reason'] = pd.Series(dtype='object')
            df_unknown['topic'] = pd.Series(dtype='object')
        else:
            # 如果不为空，进行赋值
            df_unknown.loc[:, 'dim_reason'] = '未知'
            df_unknown.loc[:, 'topic'] = '未知'

        df = df[(df.reason != 'nonsense') & (df.reason != '未知')].reset_index(drop=True)
        df['dim_reason'] = df.apply(lambda x: f"{x['dimension']}_{x['reason']}", axis=1)
        texts = df['dim_reason'].tolist()
        
        if not texts:
            print("No valid texts for embedding, skipping embedding and clustering")
            result = pd.concat([df_nonsense, df_unknown], ignore_index=True)

            print(f"标签数量：{result['mark'].nunique()}")
            print(f"数据量：{result.shape}")

            result = result[['origion', 'ids', 'clean', 'dimension', 'reason', 'dim_reason', 'topic']]

            return result

        # 向量化
        print("Please wait for embedding...")
        embedding = AzureEmbedding()
        try:
            
            embeddings = np.array(embedding.embedding(texts))
        except Exception as e:
            print(f"Error during embedding process: {str(e)}")
            raise EmbeddingError(f"Error during embedding process: {str(e)}")
        
        # 确定聚类参数
        n_samples = len(embeddings)
        if n_samples < 2:
            print("有效数据少于两条，不进行聚类")
            best_n_clusters = 1
            cluster_labels = np.zeros(n_samples, dtype=int)
        else:
            if n_samples <= 30:
                cn = [2, min(n_samples, 10)]
            else:
                cn = [6, 20]
            best_n_clusters, cluster_labels = text_cluster(embeddings, if_reduce=False, cn=cn)# 聚类

        # 聚类完成后，为每个主题收集回答原文  
        category = {i: [] for i in range(best_n_clusters)}  
        category_index = {i: [] for i in range(best_n_clusters)} 
        category_title = {i: [] for i in range(best_n_clusters)}
        for i, label in enumerate(cluster_labels):  
            category[label].append(texts[i])
            category_index[label].append(i)
        for i in range(best_n_clusters): 
            answer_list = category[i]
            try:
                title = model.chat(create_prompt_title(theme, emotion, answer_list))
            except Exception as e:
                raise ModelCallError(f"Error calling language model for title generation: {str(e)}", "title_generation")
            print(f"主题{i}：{title}：{len(answer_list)}")
            category_title[i] = title

        # 聚类主体回填
        df['topic_num'] = [label for label in cluster_labels]
        df['topic'] = [category_title[label] for label in cluster_labels]

        
        result = pd.concat([df, df_nonsense, df_unknown], ignore_index=True)
        print(f"标签数量：{result['mark'].nunique()}")
        print(f"数据量：{result.shape}")

        result = result[['origion', 'ids', 'clean', 'dimension', 'reason', 'dim_reason', 'topic']]
        
        


        # # 输出展示
        # for label in range(best_n_clusters): 
        #     topic_answers=df[df.topic_num==label].reset_index()
        #     print(f"主题{label}：{category_title[label]}，声量{len(topic_answers)}")
        #     print('回答原文：')
        #     for i,row in topic_answers.iterrows():
        #         print(f"- {row['dim_reason']}（原文：{row['clean']}）")
        #     print()

        # print('主题：未知')
        # for i,row in df_unknown.iterrows():
        #     print(row['clean'])
        # print()
        # print('主题：无意义')
        # for i,row in df_nonsense.iterrows():
        #     print(row['clean'])

        return result

    # except ModelCallError as e:
    #     print(f"模型调用错误: {e}")
    #     raise
    # except LabelingError as e:
    #     print(f"标注错误: {e}")
    #     raise
    # except EmbeddingError as e:
    #     print(f"嵌入错误: {e}")
    #     raise
    # except Exception as e:
    #     print(f"auto_analysis 中出现意外错误: {e}")
    #     raise
    

