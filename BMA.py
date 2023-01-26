# -*- coding: utf-8 -*-
"""BMA.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Lz_m9V2aCfs2S7xm0LDVQMDsuBP2K2zI
"""

import numpy as np 
import pandas as pd 
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from sklearn.model_selection import train_test_split
from itertools import combinations

from mpmath import mp
mp.dps = 50
class BMA:
    
    def __init__(self, y, X, **kwargs):
        # Setup the basic variables.
        self.y = y
        self.X = X
        self.names = list(X.columns)
        self.nRows, self.nCols = np.shape(X)
        self.likelihoods = mp.zeros(self.nCols,1)
        self.coefficients_mp = mp.zeros(self.nCols,1)
        self.coefficients = np.zeros(self.nCols)
        self.probabilities = np.zeros(self.nCols)
        # Check the max model size. (Max number of predictor variables to use in a model.)
        # This can be used to reduce the runtime but not doing an exhaustive sampling.
        if 'MaxVars' in kwargs.keys():
            self.MaxVars = kwargs['MaxVars']
        else:
            self.MaxVars = self.nCols  
        # Prepare the priors if they are provided.
        # The priors are provided for the individual regressor variables.
        # The prior for a model is the product of the priors on the variables in the model.
        if 'Priors' in kwargs.keys():
            if np.size(kwargs['Priors']) == self.nCols:
                self.Priors = kwargs['Priors']
            else:
                print("WARNING: Provided priors error.  Using equal priors instead.")
                print("The priors should be a numpy array of length equal tot he number of regressor variables.")
                self.Priors = np.ones(self.nCols)  
        else:
            self.Priors = np.ones(self.nCols)  
        if 'Verbose' in kwargs.keys():
            self.Verbose = kwargs['Verbose'] 
        else:
            self.Verbose = False 
        
    def fit(self):
        # Perform the Bayesian Model Averaging
        
        # Initialize the sum of the likelihoods for all the models to zero.  
        # This will be the 'normalization' denominator in Bayes Theorem.
        likelighood_sum = 0
        
        # To facilitate iterating through all possible models, we start by iterating thorugh
        # the number of elements in the model.
        max_likelihood = 0
        for num_elements in range(1,self.MaxVars+1): 
            
            if self.Verbose == True:
                print("Computing BMA for models of size: ", num_elements)
            
            # Make a list of all index sets of models of this size.
            Models_next = list(combinations(list(range(self.nCols)), num_elements)) 
             
            # Occam's window - compute the models to use for the next iteration
            # Models_previous: the set of models from the previous iteration that satisfy (likelihhod > max_likelihhod/20)
            # Models_next:     the set of candidate models for the next iteration
            # Models_current:  the set of models from Models_next that can be consturcted by adding one new variable
            #                    to a model from Models_previous
            if num_elements == 1:
                Models_current = Models_next
                Models_previous = []
            else:
                idx_keep = np.zeros(len(Models_next))
                for M_new,idx in zip(Models_next,range(len(Models_next))):
                    for M_good in Models_previous:
                        if(all(x in M_new for x in M_good)):
                            idx_keep[idx] = 1
                            break
                        else:
                            pass
                Models_current = np.asarray(Models_next)[np.where(idx_keep==1)].tolist()
                Models_previous = []
                        
            
            # Iterate through all possible models of the given size.
            for model_index_set in Models_current:
                
                # Compute the linear regression for this given model. 
                model_X = self.X.iloc[:,list(model_index_set)]
                model_regr = OLS(self.y, model_X).fit()
                
                # Compute the likelihood (times the prior) for the model.
                model_likelihood = mp.exp(-model_regr.bic/2)*np.prod(self.Priors[list(model_index_set)])
                    
                if (model_likelihood > max_likelihood/20):
                    if self.Verbose == True:
                        print("Model Variables:",model_index_set,"likelihood=",model_likelihood)
                    
                    # Add this likelihood to the running tally of likelihoods.
                    likelighood_sum = mp.fadd(likelighood_sum, model_likelihood)

                    # Add this likelihood (times the priors) to the running tally
                    # of likelihoods for each variable in the model.
                    for idx, i in zip(model_index_set, range(num_elements)):
                        self.likelihoods[idx] = mp.fadd(self.likelihoods[idx], model_likelihood, prec=1000)
                        self.coefficients_mp[idx] = mp.fadd(self.coefficients_mp[idx], model_regr.params[i]*model_likelihood, prec=1000)
                    Models_previous.append(model_index_set) # add this model to the list of good models
                    max_likelihood = np.max([max_likelihood,model_likelihood]) # get the new max likelihood if it is this model
                else:
                    if self.Verbose == True:
                        print("Model Variables:",model_index_set,"rejected by Occam's window")
                    

        # Divide by the denominator in Bayes theorem to normalize the probabilities 
        # sum to one.
        self.likelighood_sum = likelighood_sum
        for idx in range(self.nCols):
            self.probabilities[idx] = mp.fdiv(self.likelihoods[idx],likelighood_sum, prec=1000)
            self.coefficients[idx] = mp.fdiv(self.coefficients_mp[idx],likelighood_sum, prec=1000)
        
        # Returning the new BMA object as an output.
        return self
    
    def predict(self, data):
        data = np.asarray(data)
        try:
            result = np.dot(self.coefficients,data)
        except:
            result = np.dot(self.coefficients,data.T)
        return result  
        
    def summary(self):
        # Returning the BMA results for easy viewing.
        df = pd.DataFrame([self.names, list(self.probabilities), list(self.coefficients)], 
             ["Variable Name", "Probability", "Avg. Coefficient"]).T
        return df

df = pd.read_csv('/content/sample_data/Ganga-merged dataset.csv')
df.head()
df.dropna(inplace=True)
df.isnull().sum()

X = df[["P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11","P12","P13","P14","P15","P16","P17","P18","P19","P20","P21","P22","P23","P24","P25","P26"]]
y = df["streamfllow"]
result = BMA(y, add_constant(X), Verbose=True).fit()

result.summary()

X_train, X_test, y_train, y_test = train_test_split(
...     add_constant(X), y, test_size=0.33, random_state=42)

reg_OLS = OLS(y_train, X_train).fit()
reg_OLS.summary()

reg_BMA = BMA(y_train, X_train, Verbose=True).fit()

reg_BMA.summary()

pred_reg_BMA = reg_BMA.predict(X_test)
pred_reg_OLS = reg_OLS.predict(X_test)
pred_reg_OLS = np.asarray(pred_reg_OLS)

# Compute accuracy
errors_BMA = np.asarray(y_test)-pred_reg_BMA
errors_OLS = np.asarray(y_test)-pred_reg_OLS
RMSE_BMA = np.sqrt(np.dot(errors_BMA,errors_BMA)/len(y_test))
RMSE_OLS = np.sqrt(np.dot(errors_OLS,errors_OLS)/len(y_test))
print('Root Mean Squared Error for BMA: ',RMSE_BMA)
print('Root Mean Squared Error for OLS: ',RMSE_OLS)

idx_sort = np.argsort(np.asarray(y_test))
import matplotlib.pyplot as plt
plt.plot(pred_reg_BMA[idx_sort], 'C0', label='BMA')
plt.plot(pred_reg_OLS[idx_sort], 'C1', label='OLS')
plt.plot(np.asarray(y_test)[idx_sort] , 'C2')
leg = plt.legend();

import matplotlib.pyplot as plt
plt.plot((errors_BMA), 'C0', label='BMA')
plt.plot((errors_OLS), 'C1', label='OLS')
leg = plt.legend();

num_iters = 50
RMSE_BMA_all = np.zeros(num_iters)
RMSE_OLS_all = np.zeros(num_iters)
RMSE_BMA_all_mean = np.zeros(num_iters)
RMSE_OLS_all_mean = np.zeros(num_iters)

for i in range(num_iters):
    X_train, X_test, y_train, y_test = train_test_split(add_constant(X), y, random_state=i, test_size=0.33)# fit the models to the training data
    reg_BMA = BMA(y_train, X_train, Verbose=False).fit()
    reg_OLS = OLS(y_train, X_train).fit()
    # predict on the test data
    pred_reg_BMA = reg_BMA.predict(X_test)
    pred_reg_OLS = reg_OLS.predict(X_test)
    pred_reg_OLS = np.asarray(pred_reg_OLS)
    # Compute Root Mean Squared Error
    errors_BMA = np.asarray(y_test)-pred_reg_BMA
    errors_OLS = np.asarray(y_test)-pred_reg_OLS
    RMSE_BMA = np.sqrt(np.dot(errors_BMA,errors_BMA)/len(y_test))
    RMSE_OLS = np.sqrt(np.dot(errors_OLS,errors_OLS)/len(y_test))
    print('Root Mean Squared Error for BMA: ',RMSE_BMA)
    print('Root Mean Squared Error for OLS: ',RMSE_OLS)
    RMSE_BMA_all[i] = RMSE_BMA
    RMSE_OLS_all[i] = RMSE_OLS
    RMSE_BMA_all_mean[i] = np.sum(RMSE_BMA_all)/(i+1)
    RMSE_OLS_all_mean[i] = np.sum(RMSE_OLS_all)/(i+1)
    print('(Mean) Root Mean Squared Error for BMA: ',RMSE_BMA_all_mean[i])
    print('(Mean) Root Mean Squared Error for OLS: ',RMSE_OLS_all_mean[i])
    
print('(Mean) Root Mean Squared Error for BMA: ',np.mean(RMSE_BMA_all))
print('(Mean) Root Mean Squared Error for OLS: ',np.mean(RMSE_BMA_all))

plt.plot(RMSE_BMA_all_mean)
plt.plot(RMSE_OLS_all_mean)