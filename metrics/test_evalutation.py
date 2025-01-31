import numpy as np
from collections import Counter
import sys
import csv
csv.field_size_limit(sys.maxint)


def catlalog_coverage(total_music_size, recommend_music):
    return len(recommend_music) / float(len(total_music_size))


def RS_coverage_variation(recommend_music):
    total_size = len(recommend_music)
    count = Counter(recommend_music)
    print len(count)
    return len(count) / float(total_size)


def hit(recommend_music,num_in_user,file):
    user_list = []
    hit_rate = []
    user_index = 0
    hit_count = 0.
    cur_user = "user_000001"
    with open(file, 'rb') as tsvin:
        Input = csv.reader(tsvin, delimiter='\t')
        for row in Input:
            if (cur_user != row[0]):
                cur_user = row[0]
                for song in user_list:
                    for i in range(0,num_in_user):
                        if recommend_music[user_index][i] == song:
                            hit_count = hit_count + 1
                hit_rate.append(hit_count/len(recommend_music[user_index]))
                hit_count = 0.
                user_index = user_index + 1
                user_list = []
                user_list.append(row[5])
            else:
                user_list.append(row[5])
    print(hit_rate)
    hit_prob = sum(hit_rate) / len(hit_rate)
    return hit_prob

'''
import sys
import csv

csv.field_size_limit(sys.maxint)
from itertools import repeat

percentage = 0.8


def select_data(data_num, percentage):
    new_data_num = []
    for i in data_num:
        new_data_num.append(int(i * percentage))
    return new_data_num


user_log_num = []
count = 1
cur_user = 0
index_count = 0
index = 0
user_id = []
with open('data/test_shorter.tsv', 'rb') as tsvin:
    Input = csv.reader(tsvin, delimiter='\t')
    for row in Input:
        if (cur_user != row[0]):
            cur_user = row[0]
            user_log_num.append(count)
            count = 1
        else:
            count = count + 1
    user_log_num.append(count)

user_log_num.pop(0)
new_num = select_data(user_log_num, percentage)
chunk = 1

with open('data/test_shorter.tsv', 'rb') as tsvin, open('data/train_data.tsv', 'wb') as tsvout1, open('data/test_data.tsv', 'wb') as tsvout2:
    Input = csv.reader(tsvin, delimiter='\t')
    train = csv.writer(tsvout1)
    test = csv.writer(tsvout2)
    for row in Input:
        if (index_count <= new_num[index]):
            train.writerows([row])
            index_count = index_count + 1
        else:
            test.writerows([row])
            index_count = index_count + 1
        if (index_count == user_log_num[index]):
            index_count = 0
            index = index + 1

print(user_log_num)
print(new_num)
'''