from .common import run
NAME='Sub_PCA'; MODE='fit-then-score (unsupervised full evaluation sequence)'
def run_detector(train_data,test_data,config=None,seed=2024): return run(NAME,train_data,test_data,config,seed)
