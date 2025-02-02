import logging
import gc
import json
import numpy as np

from abc import ABC, abstractmethod
from e2eAIOK.DeNas.utils import NETWORK_LATENCY
from e2eAIOK.DeNas.scores.compute_de_score import do_compute_nas_score 
from e2eAIOK.DeNas.cv.utils.cnn import cnn_is_legal, cnn_populate_random_func
from e2eAIOK.DeNas.cv.utils.vit import vit_is_legal, vit_populate_random_func
from e2eAIOK.DeNas.nlp.utils import bert_is_legal, bert_populate_random_func, get_subconfig
from e2eAIOK.DeNas.asr.utils.asr_nas import asr_is_legal, asr_populate_random_func
from e2eAIOK.DeNas.thirdparty.utils import hf_is_legal, hf_populate_random_func
from e2eAIOK.DeNas.thirdparty.supernet_hf import SuperHFModel

 
class BaseSearchEngine(ABC):
    def __init__(self, params=None, super_net=None, search_space=None):
        super().__init__()
        self.super_net = super_net
        self.search_space = search_space
        self.params = params
        logging.basicConfig(level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('DENAS')
    
    @abstractmethod
    def search(self):
        pass

    @abstractmethod
    def get_best_structures(self):
        pass

    '''
    Judge sample structure legal or not
    '''
    def cand_islegal(self, cand):
        if self.params.domain == "cnn":
            return cnn_is_legal(cand, self.vis_dict, self.params, self.super_net)
        elif self.params.domain == "vit":
            return vit_is_legal(cand, self.vis_dict, self.params, self.super_net)
        elif self.params.domain == "bert":
            return bert_is_legal(cand, self.vis_dict, self.params, self.super_net)
        elif self.params.domain == "asr":
            is_legal, net = asr_is_legal(cand, self.vis_dict, self.params, self.super_net)
            self.super_net = net
            return is_legal
        elif self.params.domain == "hf":
            return hf_is_legal(cand, self.vis_dict, self.params)
        else:
            raise RuntimeError(f"Domain {self.params.domain} is not supported")

    '''
    Check whether candidate latency is within latency budget
    '''
    def cand_islegal_latency(self, cand):
        if "budget_latency_max" in self.params or "budget_latency_min" in self.params:
            latency = self.get_latency(cand)
            if "budget_latency_max" in self.params and self.params.budget_latency_max < latency:
                return False
            if "budget_latency_min" in self.params and self.params.budget_latency_min > latency:
                return False
        return True

    '''
    Compute candidate latency
    '''
    def get_latency(self, cand):
        if 'latency' in self.vis_dict[cand]:
            return self.vis_dict[cand]['latency']
        latency = np.inf
        if self.params.domain == "cnn":
            model = self.super_net(num_classes=self.params.num_classes, plainnet_struct=cand, no_create=False, no_reslink=False)
            latency = NETWORK_LATENCY[self.params.domain](model=model, batch_size=self.params.batch_size,
                                                                    resolution=self.params.img_size,
                                                                    in_channels=3, gpu=None, repeat_times=1,
                                                                    fp16=False)
            del model
            gc.collect()
        elif self.params.domain == "bert":
            sampled_config = {}
            sampled_config['sample_layer_num'] = cand[0]
            sampled_config['sample_num_attention_heads'] = [cand[1]]*cand[0]
            sampled_config['sample_qkv_sizes'] = [cand[2]]*cand[0]
            sampled_config['sample_hidden_size'] = cand[3]
            sampled_config['sample_intermediate_sizes'] = [cand[4]]*cand[0]
            model = self.super_net.set_sample_config(sampled_config)
            model = self.super_net
            latency = NETWORK_LATENCY[self.params.domain](model=model, batch_size=self.params.batch_size, max_seq_length=self.params.img_size, gpu=None, infer_cnt=10.)
        elif self.params.domain == "hf":
            cand_dict = json.loads(cand)
            model = SuperHFModel.set_sample_config(self.params.supernet ,**cand_dict)
            latency = NETWORK_LATENCY[self.params.domain](model=model, batch_size=self.params.batch_size, max_seq_length=self.params.img_size, gpu=None, infer_cnt=10.)
        else:
            raise RuntimeError(f"Domain {self.params.domain} is not supported")
        self.vis_dict[cand]['latency']= latency
        return self.vis_dict[cand]['latency']

    '''
    Generate sample random structure
    '''
    def populate_random_func(self):
        if self.params.domain == "cnn":
            return cnn_populate_random_func(self.super_net, self.search_space, self.params.num_classes, self.params.plainnet_struct, self.params.no_reslink, self.params.no_BN, self.params.use_se)
        elif self.params.domain == "vit":
            return vit_populate_random_func(self.search_space)
        elif self.params.domain == "bert":
            return bert_populate_random_func(self.search_space)
        elif self.params.domain == "asr":
            return asr_populate_random_func(self.search_space)
        elif self.params.domain == "hf":
            return hf_populate_random_func(self.search_space)
        else:
            raise RuntimeError(f"Domain {self.params.domain} is not supported")

    '''
    Compute nas score for sample structure
    '''
    def cand_evaluate(self, cand):
        if self.params.domain == "cnn":
            model = self.super_net(num_classes=self.params.num_classes, plainnet_struct=cand, no_create=False, no_reslink=True)
        elif self.params.domain == "vit":
            model = self.super_net
        elif self.params.domain == "bert":
            subconfig = get_subconfig(cand)
            model = self.super_net.set_sample_config(subconfig)
            model = self.super_net
        elif self.params.domain == "asr":
            model = self.super_net
        elif self.params.domain == "hf":
            subconfig = json.loads(cand)
            model = SuperHFModel.set_sample_config(self.params.supernet, **subconfig)
        else:
            raise RuntimeError(f"Domain {self.params.domain} is not supported")
        
        nas_score, score, latency = do_compute_nas_score(model_type = self.params.model_type, model=model, 
                                                        resolution=self.params.img_size,
                                                        batch_size=self.params.batch_size,
                                                        mixup_gamma=1e-2,
                                                        expressivity_weight=self.params.expressivity_weight,
                                                        complexity_weight=self.params.complexity_weight,
                                                        diversity_weight=self.params.diversity_weight,
                                                        saliency_weight=self.params.saliency_weight,
                                                        latency_weight=self.params.latency_weight)
        self.vis_dict[cand]['score'] = nas_score
        return nas_score, score, latency