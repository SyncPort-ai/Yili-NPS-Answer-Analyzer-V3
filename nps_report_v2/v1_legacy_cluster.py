"""
V1 Cluster模块的完整副本 - 用于V2系统内部调用
保持与原始cluster.py完全一致的逻辑
重命名为v1_legacy_cluster.py避免混淆
"""
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def text_cluster(embeddings,if_reduce=True,number_clusters=None,cn=[6,20]):
    
    # 特征降维
    if if_reduce == True:
       
        pca = PCA(n_components=min(100,len(embeddings)))
        reduced_embeddings = pca.fit_transform(embeddings)
        print(f"数据量：{len(reduced_embeddings)}，维度：{len(reduced_embeddings[0])}")
        embeddings=reduced_embeddings
   
    """
    
    import matplotlib.pyplot as plt 
    
    # elbow肘部法则——计算不同聚类数的SSE,选择下降幅度突然变小的cluster
    sse = {} 
    for k in range(10, 30):  # 尝试从1到10的聚类数  
        kmeans = KMeans(n_clusters=k, random_state=0).fit(embeddings)  
        sse[k] = kmeans.inertia_  # inertia_是聚类内的平方和  
    m=plt.figure() 
    m=plt.plot(list(sse.keys()), list(sse.values()),'*-')  
    m=plt.xlabel('Number of clusters')  
    m=plt.ylabel('SSE')  
    plt.show() 
    
    # 轮廓系数——选择最高点
    score=[]
    for k in range(10,30):
        kmeans=KMeans(n_clusters=k)
        m=kmeans.fit(reduced_embeddings)
        score.append(silhouette_score(embeddings,kmeans.labels_,metric='euclidean'))
    m=plt.plot(range(10,30),score,'r*-')
    m=plt.xlabel(u'k')
    m=plt.ylabel(u'Number of clusters')
    m=plt.title(u'K值')
    plt.show()
    
    """
    # 确定最佳簇数
    if number_clusters == None:    
        # 自动计算最佳轮廓系数
        range_n_clusters = list(range(cn[0], cn[1]))
        best_n_clusters = cn[0]
        best_silhouette_avg = -1
        for k in range_n_clusters:
            kmeans = KMeans(n_clusters=k, random_state=42)
            cluster_labels = kmeans.fit_predict(embeddings)
            score = silhouette_score(embeddings, cluster_labels)
            if score > best_silhouette_avg:
                best_n_clusters = k
                best_silhouette_avg = score
    else:
        best_n_clusters = number_clusters

    # 使用最佳聚类数重新进行聚类  
    kmeans = KMeans(n_clusters=best_n_clusters, random_state=0).fit(embeddings)  
    cluster_labels = kmeans.labels_ 
    # 评估聚类结果
    score = silhouette_score(embeddings, kmeans.labels_)
    print(f"best_n_clusters:{best_n_clusters},\nscore:{best_silhouette_avg}")

    return best_n_clusters, cluster_labels