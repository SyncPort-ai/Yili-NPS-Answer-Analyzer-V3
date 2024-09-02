import os
import requests
import base64


class AzureChat():
    def  __init__(self, 
                  GPT4V_KEY:str="37ae2a35c80c4b42b9d6ff8793ce472b",
                  GPT4V_ENDPOINT:str = "https://gpt4-turbo-sweden.openai.azure.com/openai/deployments/only_for_yili_test_4o_240710/chat/completions?api-version=2024-02-15-preview")-> str:
        self.GPT4V_KEY = GPT4V_KEY
        self.GPT4V_ENDPOINT = GPT4V_ENDPOINT
        
    def chat(self, prompt):
        try:        
            headers = {
                "Content-Type": "application/json",
                "api-key": self.GPT4V_KEY,
            }
            payload = {
              "messages": [
                {
                  "role": "system",
                  "content": [
                    {
                      "type": "text",
                      "text": prompt
                    }
                  ]
                }
              ],
              "temperature": 0.5,
              "top_p": 0.95,
              "max_tokens": 1800
            }
            response = requests.post(self.GPT4V_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
            
        except requests.RequestException as e:
            raise SystemExit(f"Failed to make the request. Error: {e}")
    
        return response.json()['choices'][0]['message']['content']

class AzureChatApp():
    def  __init__(self, 
                  url = 'https://ycsb-gw-pub.xapi.digitalyili.com/restcloud/yili-gpt-prod/v1/getTextToThird',
                  app_key = '649aa4671fa7b91962caa01d'):
        self.url = url
        self.app_key = app_key
        
    def chat(self,prompt):
        try:
            headers = {  
                'AppKey': self.app_key,  
                'Content-Type': 'application/json' 
            } 
            data = {  
                "channelCode": "wvEO", 
                "tenantsCode": "Yun8457",
                "choiceModel":1,
                "isMultiSession":1,
                "requestContent": prompt,  
                "requestType": 1,  
                #"responseLengthLimit":8000,
                "streamFlag":0,
                "userCode": "wvEO10047252", 
                "requestGroupCode": "1243112808144896"
            }  
    
            response = requests.post(self.url, json=data, headers=headers)       
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
            
        except requests.RequestException as e:
            raise SystemExit(f"Failed to make the request. Error: {e}")
    
        return response.json()['data']['responseVO']

import time
class AzureEmbedding():
    def __init__(self,
                 key="37ae2a35c80c4b42b9d6ff8793ce472b",
                 api_version="2024-06-01",#"2023-12-01-preview"
                 endpoint="https://gpt4-turbo-sweden.openai.azure.com/",
                model="text-embedding-ada-002"#"text-embedding-3-large"
                ):
        from openai import AzureOpenAI
        
        self.client = AzureOpenAI(
            api_key = os.getenv("AZURE_OPENAI_API_KEY",key),  
            api_version = api_version,
            azure_endpoint =os.getenv("AZURE_OPENAI_API_KEY",endpoint))
        self.model=model
        
    def embedding(self,texts):
        
        start_time=time.time()
        
        response = self.client.embeddings.create(input = texts,model= self.model)
        embeddings=[response.data[i].embedding for i in range(len(response.data))]
        
        end_time=time.time()
        print(f"文本数量（{len(response.data)}）向量维度（{len(response.data[0].embedding)}）调用embedding耗时{end_time-start_time}秒")
    
        return embeddings