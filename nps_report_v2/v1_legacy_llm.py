"""
V1 LLM模块的完整副本 - 用于V2系统内部调用
保持与原始llm.py完全一致的逻辑
重命名为v1_legacy_llm.py避免混淆
"""
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
              "temperature": 0.1,
              "top_p": 0.95,
              "max_tokens": 4000
            }

            response = requests.post(self.GPT4V_ENDPOINT, headers=headers, json=payload)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"AzureChat error: {e}")
            if 'response' in locals():
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
            raise


class AzureChatApp():
    def  __init__(self)-> str:
        self.OPENAI_BASE_URL_YL="http://ai-gateway.yili.com/v1/"
        self.API_KEY = "app_gSbfxY2bYLl8bOxjJJeGT"
        
    def chat(self, prompt):
        try:        
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.API_KEY}",
            }
            payload = {
              "model": "gpt-4-turbo",
              "messages": [
                {
                  "role": "system",
                  "content": prompt
                }
              ],
              "temperature": 0.1,
              "top_p": 0.95,
              "max_tokens": 4000
            }

            response = requests.post(f"{self.OPENAI_BASE_URL_YL}chat/completions", headers=headers, json=payload, timeout=60)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"AzureChatApp error: {e}")
            if 'response' in locals():
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
            raise


class AzureEmbedding():
    def __init__(self, 
                 API_KEY:str="37ae2a35c80c4b42b9d6ff8793ce472b",
                 ENDPOINT:str="https://gpt4-turbo-sweden.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2023-05-15") -> str:
        self.API_KEY = API_KEY
        self.ENDPOINT = ENDPOINT
        
    def embedding(self, texts):
        try:
            headers = {
                "Content-Type": "application/json",
                "api-key": self.API_KEY,
            }
            payload = {
                "input": texts
            }

            response = requests.post(self.ENDPOINT, headers=headers, json=payload)
            embeddings = [data['embedding'] for data in response.json()['data']]
            return embeddings
        except Exception as e:
            print(f"AzureEmbedding error: {e}")
            if 'response' in locals():
                print(f"Response status: {response.status_code}")
                print(f"Response content: {response.text}")
            raise