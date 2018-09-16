
# coding: utf-8

# In[2]:


#init cash
import riot_api_v1 as riot
riot.initcash(fromfile=True)


# In[3]:


len(riot.players)


# In[4]:


len(riot.cashedmatches)


# In[49]:


import numpy as np
import pandas as pd
matches = pd.DataFrame(riot.cashedmatches)
matches.head(5)


# In[87]:


matches.shape


# In[88]:


# 0 - win 100 ; 1 - win 200
y = matches[[2]]/100-1
y.head()


# In[115]:


#x = matches[matches.columns[13:23]]
x = matches.iloc[:,13:23].copy()
x.head()


# In[90]:


champions = np.unique(x[:])
print(champions)


# In[137]:


results = np.zeros((len(x), 2*len(champions)))


# In[138]:


results.shape


# In[139]:


for i in range(len(x)):
    for j in range(len(champions)):
        for c in range(13,18):
            if champions[j]==x.loc[i,c]:
                results[i,j]=1.0
        for c in range(18,23):
            if champions[j]==x.loc[i,c]:
                results[i,j+141]=1.0


# In[183]:


#find champions
import json
file = open(riot.FILE_CHAMPIONS, 'r')
data = json.load(file)
file.close()
names = {value['id']:value['key'] for value in data['data'].values()}

test1 = []
for k,v in enumerate(results[0]):
    if v==1:
        if k<141:
            test1.append(names[champions[k]])
        else:
            test1.append(names[champions[k-141]])
print('in results:',test1)
test2 = [names[i] for i in x.iloc[0]]
print('in match:',test2)


# In[185]:


import tensorflow as tf
from tensorflow import keras

import numpy as np
import matplotlib.pyplot as plt

print(tf.__version__)
from sklearn.model_selection import train_test_split


# In[186]:


X_train, X_test, y_train, y_test = train_test_split(results, y, test_size=0.3)
print (X_train.shape, y_train.shape)
print (X_test.shape, y_test.shape)


# In[190]:


baseline_model = keras.Sequential([
    # `input_shape` is only required here so that `.summary` works. 
    keras.layers.Dense(16, activation=tf.nn.relu, input_shape=(282,)),
    keras.layers.Dense(16, activation=tf.nn.relu),
    keras.layers.Dense(1, activation=tf.nn.sigmoid)
])

baseline_model.compile(optimizer='adam',
                       loss='binary_crossentropy',
                       metrics=['accuracy', 'binary_crossentropy'])

baseline_model.summary()


# In[191]:


baseline_history = baseline_model.fit(X_train,
                                      y_train,
                                      epochs=50,
                                      batch_size=50,
                                      validation_data=(X_test, y_test),
                                      verbose=2)

