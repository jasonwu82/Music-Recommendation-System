import time
import numpy as np
from scipy.sparse import coo_matrix, lil_matrix
from sklearn.cluster import DBSCAN
from sklearn.cluster import KMeans

def get_lyrics_dict(sp_tra,df):
    df = df.rename(columns={ df.columns[0] : 'traname'})
    df["traname"] = df["traname"].apply(lambda x: x[2:-1])
    tra2vec_df = df.set_index("traname")
    
    tra2vec_dict = {}
    for traname in tra2vec_df.index:
        vec = tra2vec_df.loc[traname].as_matrix()
        if vec.ndim != 1:
            print (traname,vec.shape[0])
            vec = vec[0]
        mat = np.array(vec,dtype=np.float32).reshape((5,300))
        tra2vec_dict[traname] = np.mean(mat,axis=0) # Use mean to stand song (1,300)
    #print ("song collected:",len(tra2vec_dict.items()))
    return tra2vec_dict

def sp_shrink(sp,sp_tra,word2vec_dict):
    reduce_tra_idx = [ i for i,x in enumerate(sp_tra) if x in word2vec_dict.keys() ]
    reduce_tra = sp_tra[reduce_tra_idx]
    reduce_mat = sp[:,reduce_tra_idx]
    #print ("song reduced:",reduce_mat.shape[1])
    return reduce_mat,reduce_tra

def user_encode(sp, sp_tra,word2vec_df):
    # Retrieve lyrics vec
    # Return user-vec matrix
    
    tra2vec_dict = get_lyrics_dict(sp_tra,word2vec_df)
    rate_mat,tra = sp_shrink(sp,sp_tra,tra2vec_dict)
    
    N_user, N_item = rate_mat.shape
    encode_mat = np.zeros((N_user,300))
    
    for i in range(N_user):
        weight_vec = np.zeros(300)
        weight_sum = 1 # need add back
        for loc in rate_mat[i].nonzero()[1]:
            score = rate_mat[i,loc]
            weight_vec += score * tra2vec_dict[ tra[loc] ]
            weight_sum += score
        encode_mat[i] = weight_vec / weight_sum
    return rate_mat,encode_mat,tra

def recommend_all(user_item,pred,repeat=False):
    if repeat == True:
        return np.argsort(-pred.todense(),axis=1)
    cand = user_item != pred
    loc = cand.nonzero()
    rec = np.zeros(pred.shape)
    pred = pred.todense()
    rec[loc] = pred[loc]
    return np.argsort(-rec, axis=1)

def get_songs_by_indices(mat,tra,n_top=3):
    # Transform evaluation result
    # idx to string
    mat = mat[:,:n_top]
    N_usr,N_top = mat.shape
    songs = np.copy(mat).tolist()
    for i in range(N_usr):
        for j in range(N_top):
            songs[i][j] = tra[mat[i,j]]
    return songs

def user_kmeans(rate_mat, k=1):
    # Clustering using of users
    # Fill matrix with the centers

    kmeans = KMeans(n_clusters=k, random_state=0).fit(rate_mat)
    usr_labels, usr_cluster_c = kmeans.labels_, kmeans.cluster_centers_
    return usr_labels, usr_cluster_c

def get_cluster_c(rate_mat,usr_labels):
    N_user, N_item = rate_mat.shape
    # Construct cluster_c using labels (sparse)
    cls_num, cnt_cls = np.unique(usr_labels, return_counts=True)
    n_cls = len(cls_num)
    usr_cluster_c = lil_matrix((n_cls,N_item))
    for i, i_cls in enumerate(usr_labels):
        usr_cluster_c[i_cls] += rate_mat[i] / cnt_cls[i_cls]
    return usr_cluster_c

def fill_matrix(rate_mat,usr_labels,fill_rate=0.3):
    N_user, N_item = rate_mat.shape
    def get_zero_loc(usr_rate):
        rate = usr_rate.count_nonzero() / N_item
        #print ("fill rate:",rate)
        if rate > fill_rate: # full enough
            return []
        idx = np.random.choice(N_item, int(np.ceil(N_item*fill_rate)), replace=False)
        vec = np.zeros((1, N_item),dtype=bool)  # sp no vector
        vec[0,idx] = 1

        sp_vec = usr_rate.toarray().astype(bool)
        loc_vec = np.logical_xor(np.logical_or(sp_vec, vec), sp_vec) # avoid filling nonzero loc
        loc = np.where(loc_vec != 0)
        if len(loc[0]) != 0:
            return loc # (loc[x],loc[y])
        return []

    usr_cluster_c = get_cluster_c(rate_mat,usr_labels)

    # Fill matrix, use lil_matrix to change will be faster!
    rate_mat = rate_mat.tolil() 
    for i, i_cls in enumerate(usr_labels):
        user_rate = rate_mat[i] # (1,N_item)
        revise_loc = get_zero_loc(user_rate) # Fill out the rate_mat if cap < threshold
        if len(revise_loc) != 0:
            rate_mat[i,revise_loc[1]] = usr_cluster_c[i_cls, revise_loc[1]]
    
    #np.argsort(-usr_cluster_c.todense(),axis=1)
    return rate_mat

def fill_matrix2(rate_mat,usr_labels,fill_rate=0.3):
    N_user, N_item = rate_mat.shape
    N_fill = int(np.ceil(N_item*fill_rate))
    usr_cluster_c = get_cluster_c(rate_mat,usr_labels)

    #loc = rate_mat.nonzero()
    rate_mat = rate_mat.tolil() 

    for i, i_cls in enumerate(usr_labels):
        usr_c = usr_cluster_c[i_cls].copy()
        loc = rate_mat[i].nonzero()
        usr_c[0,loc[1]] = 0
        N_occupied = usr_cluster_c[i_cls].getnnz() - usr_c.getnnz()
        if N_occupied >= N_fill:
            continue
        N_revise = N_fill - N_occupied # Num still need to fill
        #print ("User {} should fill {} entries,{} occupied, {} need revise but {} ".format(i,N_fill,N_occupied,N_revise,usr_c.getnnz()))
        N_revise = min(N_revise,usr_c.getnnz())
        #N_emtpy = N_item - N_occupied
        #N_fill = min(N_item - N_occupied,N_fill)
        #print ("N_fill:",N_fill)
        #print (usr_c.getnnz(),N_fill)
        #break
        
        # N_fill
        usr_c_sort_idx = np.argsort(-np.abs(usr_c.todense()),axis=1)
        #N_fill = (N_fill - usr_c.getnnz()) if usr_c.getnnz() < N_fill else N_fill
        revise_loc = usr_c_sort_idx[0,:N_revise] # Todo
        rate_mat[i,revise_loc[0,:]] = usr_cluster_c[i_cls, revise_loc[0,:]]
    return rate_mat

def cluster_usr(rate_mat, k=1, min_rate=0.1, add_rate=0.01):
    # Clustering using of users
    # Fill matrix with the centers

    N_user, N_item = rate_mat.shape
    print ("Matrix: {}x{}" .format(N_user, N_item))
    start_time = time.time()
    kmeans = KMeans(n_clusters=k, random_state=0).fit(rate_mat)
    user_labels, user_cluster_c = kmeans.labels_, kmeans.cluster_centers_
    print("k-means (k={}) took {} sec".format(k, time.time() - start_time))

    def get_zero_loc(usr_rate):
        rate = np.sum(usr_rate,axis=1)[0,0] / N_item
        # print ("fill rate:",rate)
        if rate > min_rate: # full enough
            return []
        idx = np.random.choice(N_item, int(N_item * add_rate), replace=False)
        vec = np.zeros((1, N_item),dtype=bool)  # sp no vector
        vec[0,idx] = 1

        sp_vec = usr_rate.toarray().astype(bool)
        loc_vec = np.logical_xor(np.logical_or(sp_vec, vec), sp_vec) # avoid filling nonzero loc
        return np.where(loc_vec != 0)
        # return idx

    start_time = time.time()
    for i, i_cls in enumerate(user_labels):
        user_rate = rate_mat[i] # (1,N_item)
        revise_loc = get_zero_loc(user_rate) # Fill out the rate_mat if cap < threshold
        if len(revise_loc) != 0:
            rate_mat[i,revise_loc] = user_cluster_c[i_cls, revise_loc]
    print("filling took {} sec".format(time.time() - start_time))


if __name__ == "__main__":

    # Dummy input: Init with 0/1 (Listening counts)
    N_usr = 100
    N_item = 100

    rate_mat = np.random.choice([0, 1], size=(N_usr, N_item), p=[1. / 3, 2. / 3]).astype(np.float16)
    print ("origin: {} / {}".format(np.count_nonzero(rate_mat), N_usr * N_item))

    k = 2  # kmeans
    fill_matrix(rate_mat, k)
    print ("fill: {} / {}".format(np.count_nonzero(rate_mat), N_usr * N_item))
