import sys,inspect
sys.path.insert(0,r'D:\CSIES\TSAD\Onelier\CDU_starter_kit\cdu_kit')
sys.path.insert(0,r'D:\CSIES\AI4Energy\others\TSB-AD')
from vus_eval import basic_metrics
print(basic_metrics.__file__)
print(inspect.getsource(basic_metrics.generate_curve))
