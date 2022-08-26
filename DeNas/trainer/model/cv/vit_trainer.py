import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from TorchTrainer import BaseTrainer
import torch.nn as nn
import torch
import random
from model.cv.vit_model_builder import *
from data_builder import *
from timm.scheduler import create_scheduler
from timm.optim import create_optimizer
from argparse import Namespace
from pathlib import Path
import utils
from model.cv.init_vit_parser import init_vit_parser
import argparse
import datetime
import time
from pathlib import Path
from typing import Iterable, Optional
import math
from timm.utils import accuracy
import extend_distributed as ext_dist

class ViTTrainer(BaseTrainer):
    def __init__(self, args):
        
        parser = init_vit_parser(args)
        self.args = parser.parse_args(args)
        print(F"vit args:{self.args}")
        self.data_path = self.args.data_path
        self.model_builder = ViTModelBuilder(self.args)
        ext_dist.init_distributed(backend=self.args.dist_backend)

    
    def train_one_epoch(self, model: torch.nn.Module, criterion: torch.nn.Module,
                    data_loader: Iterable, optimizer: torch.optim.Optimizer,
                    epoch: int):
        model.train()
        criterion.train()

        # set random seed
        random.seed(epoch)

        metric_logger = utils.MetricLogger(delimiter="  ")
        metric_logger.add_meter('lr', utils.SmoothedValue(window_size=1, fmt='{value:.6f}'))
        header = 'Epoch: [{}]'.format(epoch)
        print_freq = 10


        for inputs, targets in metric_logger.log_every(data_loader, print_freq, header):
            outputs = model(inputs)
            loss = criterion(outputs, targets)

            loss_value = loss.item()

            if not math.isfinite(loss_value):
                print("Loss is {}, stopping training".format(loss_value))
                sys.exit(1)

            optimizer.zero_grad()       
            loss.backward()
            optimizer.step()

        
            metric_logger.update(loss=loss_value)
            metric_logger.update(lr=optimizer.param_groups[0]["lr"])

        # gather the stats from all processes
        metric_logger.synchronize_between_processes()
        print("Averaged stats:", metric_logger)
        return {k: meter.global_avg for k, meter in metric_logger.meters.items()}

    @torch.no_grad()
    def evaluate(self, data_loader, model):
        criterion = torch.nn.CrossEntropyLoss()

        metric_logger = utils.MetricLogger(delimiter="  ")
        header = 'Test:'

        # switch to evaluation mode
        model.eval()

        for inputs, target in metric_logger.log_every(data_loader, 10, header):
            

            output = model(inputs)
            
            loss = criterion(output, target)

            acc1, acc5 = accuracy(output, target, topk=(1, 5))

            batch_size = inputs.shape[0]
            metric_logger.update(loss=loss.item())
            metric_logger.meters['acc1'].update(acc1.item(), n=batch_size)
            metric_logger.meters['acc5'].update(acc5.item(), n=batch_size)
        # gather the stats from all processes
        metric_logger.synchronize_between_processes()
        print('* Acc@1 {top1.global_avg:.3f} Acc@5 {top5.global_avg:.3f} loss {losses.global_avg:.3f}'
            .format(top1=metric_logger.acc1, top5=metric_logger.acc5, losses=metric_logger.loss))

        return {k: meter.global_avg for k, meter in metric_logger.meters.items()}     
        
    def fit(self):
        args = self.args
        data_loader_train,  data_loader_val = DataBuilder(args).get_data(ext_dist)
        output_dir = Path(args.output_dir)

        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        with open(args.best_model_structure, 'r') as f:
            arch = f.readlines()[-1]
        model = self.model_builder.create_model(arch, ext_dist)
        criterion = torch.nn.CrossEntropyLoss()
        optimizer = create_optimizer(args, model)
        lr_scheduler, _ = create_scheduler(args, optimizer)
        print("Start training")
        start_time = time.time()
        max_accuracy = 0.0
        for epoch in range(args.epochs):
            train_stats = self.train_one_epoch(
                model, criterion, data_loader_train,
                optimizer, epoch)

            lr_scheduler.step(epoch)

            test_stats = self.evaluate(data_loader_val, model)
            max_accuracy = max(max_accuracy, test_stats["acc1"])
            print(f'Max accuracy: {max_accuracy:.2f}%')
            if args.output_dir:
                checkpoint_paths = [output_dir / 'checkpoint.pth']
                for checkpoint_path in checkpoint_paths:
                    utils.save_model({
                        'model': model.state_dict(),
                        'optimizer': optimizer.state_dict(),
                        'lr_scheduler': lr_scheduler.state_dict(),
                        'epoch': epoch,
                        'args': args,
                    }, checkpoint_path)
            log_stats = {**{f'train_{k}': v for k, v in train_stats.items()},
                        **{f'test_{k}': v for k, v in test_stats.items()},
                        'epoch': epoch}

            if args.output_dir and utils.is_main_process():
                with (output_dir / "log.txt").open("a") as f:
                    f.write(json.dumps(log_stats) + "\n")
        total_time = time.time() - start_time
        total_time_str = str(datetime.timedelta(seconds=int(total_time)))
        print('Training time {}'.format(total_time_str))


            
    



    