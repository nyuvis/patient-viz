#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on 2015-04-16

@author: narges
"""
from __future__ import print_function
import sys
import os.path
import csv
import random

import numpy as np
from sklearn import cross_validation
from sklearn import linear_model
from sklearn.metrics import roc_curve,auc
import cPickle

def parsedata(cohort):
    cohortsize = -1
    data = None
    head = None
    with open(cohort, 'r') as csvfile:
        cohortsize = len(csvfile.readlines()) - 1
        #------
        csvfile.seek(0)
        for (ix, row) in enumerate(csv.DictReader(csvfile)):
            if head is None:
                head = filter(lambda h: h != 'id', row.keys())
                # position test and outcome correctly
                # 0 will be test
                # 1 will be outcome
                head[head.index('test')] = head[0]
                head[head.index('outcome')] = head[1]
                head[0] = 'test'
                head[1] = 'outcome'
            if data is None:
                data = np.zeros((cohortsize, len(head)), dtype='bool')
            data[ix,:] = np.array(map(lambda k: row[k], head))
        #-----
        # test column is 0 and output column is 1
        test_ix = data[:,0]
        testsetx = data[(test_ix==1),2:]
        testsety = data[(test_ix==1),1]
        trainsetx = data[(test_ix==0),2:]
        trainsety = data[(test_ix==0),1]
    return trainsety, trainsetx, testsety, testsetx, head[2:]

def getsavefile(filename, ext, overwrite):
    save_name = filename
    if not overwrite:
        count = 0
        while os.path.exists(save_name + ext):
            save_name = filename + "_" + str(count)
            count += 1
        print('{0} file exists. saving as {1}{2}'.format(filename, save_name, ext), file=sys.stderr)
    return save_name + ext

def buildmodel(cohort, model, validPercentage, seed, modeloutput, overwrite):
    trainsety, trainsetx, testsety, testsetx, header = parsedata(cohort)

    if model == 'reg':
        # c_list can come from a config file eventually.
        c_list = [0.01, 0.1, 1, 10, 100]
        total = int(np.floor(100.0/validPercentage))
        score_array = np.zeros((total, len(c_list)), dtype='float')
        for run_ix in range(0,total):
            X_train, X_valid, y_train, y_valid = cross_validation.train_test_split(trainsetx, trainsety, test_size=(validPercentage/100.0), random_state=seed+run_ix)
            for (c_ix, c) in enumerate(c_list):
                #more parametrization of model can come from some config file eventually.
                model_c  = linear_model.LogisticRegression(penalty='l1', C=c, fit_intercept='true', class_weight='auto')
                model_c.fit(X_train,y_train)
                Ypred_valid = model_c.predict_proba(X_valid)
                # evaluation metric could come from a config file eventually. currently AUC is commonly used and we use here
                fprs, tprs, thresholdss = roc_curve(y_valid, Ypred_valid[:,1])
                score_c = auc(fprs,tprs)
                score_array [run_ix, c_ix] = score_c

        mean_scores = score_array.mean(axis=0)
        mean_scores_ix = np.argmax(mean_scores)
        best_c = c_list[mean_scores_ix]
        #now train on the entire train set, using best c:
        model_best_c  = linear_model.LogisticRegression(penalty='l1', C=best_c, fit_intercept='true', class_weight='auto')
        model_best_c.fit(trainsetx,trainsety)
        #----
        Ypred_test = model_best_c.predict_proba(testsetx)
        fprs, tprs, thresholdss = roc_curve(testsety, Ypred_test[:,1])
        Ypred_train = model_best_c.predict_proba(trainsetx)
        fprt, tprt, thresholdst = roc_curve(trainsety, Ypred_train[:,1])
        print('score on unseen test set is: ', auc(fprs,tprs), file=sys.stderr)
        print('training score on this set was: ', auc(fprt,tprt), file=sys.stderr)
        print("best average score during cross validation was:", mean_scores[mean_scores_ix], "with c =", best_c, file=sys.stderr)
        #----
        print('saving the model in directory: ', modeloutput, file=sys.stderr)
        if not os.path.exists(modeloutput):
            os.makedirs(modeloutput)
        save_name = getsavefile(modeloutput + "/reg_model_scklearn", ".pkl", overwrite)
        cPickle.dump(model_best_c, open(save_name, 'wb'), -1)
        save_name = getsavefile(modeloutput + "/reg_model_weights", ".txt", overwrite)
        np.savetxt(save_name, model_best_c.coef_, delimiter=',', header=','.join(header), comments='')
        save_name = getsavefile(modeloutput + "/reg_model_bias", ".txt", overwrite)
        np.savetxt(save_name, model_best_c.intercept_)
    elif model == 'SVM' or model == 'randForest':
        print('{0} model not implemented yet'.format(model), file=sys.stderr)
        exit(1)
    else:
        print('unknown model {0}'.format(model), file=sys.stderr)
        exit(1)

def usage():
    print('usage: {0} [-hw] --in <input file> --out <output dir> [-v <validation size>] [--seed <seed>] [--model <model type>]'.format(sys.argv[0]), file=sys.stderr)
    print('-h: print help', file=sys.stderr)
    print('-w: if set output files get overwritten', file=sys.stderr)
    print('-v <percentage>: specifies the percentage (0-100) of patients in the training set, used for tuning parameters of the model. default is 20', file=sys.stderr)
    print('--in <input file>: specifies the feature vectors', file=sys.stderr)
    print('--out <output dir>: specifies model output directory', file=sys.stderr)
    print('--seed <seed>: specifies the seed for the rng. if omitted the seed is not set. needs to be integer', file=sys.stderr)
    print('--model <model type>: specifies what type of model is to be trained. default is reg(logistic regression) options:reg|randForest|SVM', file=sys.stderr)
    exit(1)

if __name__ == '__main__':
    overwrite = False
    seed = int(np.random.rand(1)*1000) #randomly initialize, unless specified
    validPercentage = 20
    cohort = ""
    modeloutput = ""
    model = 'reg'
    args = sys.argv[:]
    args.pop(0)
    while args:
        arg = args.pop(0)
        if arg == '-h':
            usage()
        if arg == '-w':
            overwrite = True
        elif arg == '--in':
            if not len(args):
                print('--in requires input file ', file=sys.stderr)
                usage()
            cohort = args.pop(0)
        elif arg == '--out':
            if not len(args):
                print('--out requires model output directory', file=sys.stderr)
                usage()
            modeloutput = args.pop(0)
        elif arg == '-v':
            if not len(args):
                print('-v requires percentage', file=sys.stderr)
                usage()
            try:
                validPercentage = float(args.pop(0))
            except:
                print('-v requires percentage', file=sys.stderr)
                usage()
        elif arg == '--seed':
            if not len(args):
                print('--seed requires integer seed', file=sys.stderr)
                usage()
            try:
                seed = int(args.pop(0))
                np.random.seed(seed)
            except:
                print('--seed requires integer seed', file=sys.stderr)
                usage()
        elif arg == '--model':
            if not len(args):
                print('--model requires type of model from: reg|randForest|SVM', file=sys.stderr)
                usage()
            model = args.pop(0)
        else:
            print('unrecognized argument: ' + arg, file=sys.stderr)
            usage()

    if not len(cohort):
        print('requires input file', file=sys.stderr)
        usage()

    if not len(modeloutput):
        print('requires output directory', file=sys.stderr)
        usage()

    buildmodel(cohort, model, validPercentage, seed, modeloutput, overwrite)
