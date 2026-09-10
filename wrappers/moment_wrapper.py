from .common import run
# TSB-AD exposes distinct ZS and FT protocols. They must remain distinct rows.
def run_detector(train_data,test_data,config=None,seed=2024,profile='MOMENT_ZS'):
    if profile not in {'MOMENT_ZS','MOMENT_FT'}: raise ValueError(profile)
    return run(profile,train_data,test_data,config,seed)
