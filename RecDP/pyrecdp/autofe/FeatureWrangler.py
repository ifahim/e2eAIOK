from pyrecdp.primitives.generators import *
from .BasePipeline import BasePipeline
import logging
from pyrecdp.core.dataframe import DataFrameAPI
from pyrecdp.core import SeriesSchema
import pandas as pd
import copy

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.ERROR, datefmt='%I:%M:%S')
logger = logging.getLogger(__name__)

class FeatureWrangler(BasePipeline):
    def __init__(self, dataset, label, supplementary_datasets = None, *args, **kwargs):
        super().__init__(dataset, label)
        self.data_profiler = [cls() for cls in feature_infer_list]
        self.pre_feature = [cls() for cls in label_feature_generator_list]
        # If we provided multiple datasets in this workload
        self.generators.append([cls() for cls in pre_feature_generator_list])
        self.generators.append([cls() for cls in transformation_generator_list])
        self.generators.append([cls() for cls in pre_enocode_feature_generator_list])
        self.generators.append([cls() for cls in index_generator_list])
        self.generators.append([cls() for cls in encode_generator_list])
        self.generators.append([cls() for cls in post_feature_generator_list])
        self.generators.append([cls(final = True) for cls in final_generator_list])

        self.fit_analyze()

    def fit_analyze(self, *args, **kwargs):
        X = DataFrameAPI().instiate(self.dataset[self.main_table])
        sampled_data = X.may_sample()
        child = list(self.pipeline.keys())[-1]
        max_id = child
        if self.y is not None:
            # insert label process to pipeline            
            cur_id = child
            original_first_op = copy.deepcopy(self.pipeline[cur_id])
            self.pipeline[cur_id] .output = [SeriesSchema(self.y)]
            
            for generator in self.data_profiler:
                self.pipeline, child, max_id = generator.fit_prepare(self.pipeline, [child], max_id, pd.DataFrame(sampled_data[self.y.name]))
            for generator in self.pre_feature:
                self.pipeline, child, max_id = generator.fit_prepare(self.pipeline, [child], max_id)
            
            cur_id = max_id + 1
            original_first_op.idx = cur_id
            original_first_op.op = "DataFrame"
            original_first_op.children = [child]
            self.pipeline[cur_id] = original_first_op            
            max_id = cur_id
            child = cur_id
            sampled_data = sampled_data[self.feature_columns]
        
        for generator in self.data_profiler:
            self.pipeline, child, max_id = generator.fit_prepare(self.pipeline, [child], max_id, sampled_data)
        super().fit_analyze(*args, **kwargs)