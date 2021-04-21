# Copyright 2018 The LogPAI Team (https://github.com/logpai).
#
# Licensed under the MIT License:
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights 
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.
# =============================================================================
""" 
This file implements the regular expression based algorithm for log 
template matching. The algorithm is described in the following paper:

[1] Jieming Zhu, Jingyang Liu, Pinjia He, Zibin Zheng, Michael R. Lyu. 
    "Real-Time Log Event Matching at Scale", XXX, 2018.
"""

from ..utils import logloader
from collections import defaultdict, Counter, OrderedDict
import re
import pandas as pd
import os
from datetime import datetime
import multiprocessing as mp
import itertools
import hashlib
import numpy as np


class PatternMatch(object):

    def __init__(self, outdir='./result/', n_workers=1, optimized=False, logformat=None):
        self.outdir = outdir
        if not os.path.exists(outdir):
            os.makedirs(outdir) # Make the result directory
        self.template_match_dict = defaultdict(dict)
        self.template_freq_dict = Counter()
        self.logformat = logformat
        self.n_workers = n_workers
        self.optimized = optimized

    def add_event_template(self, event_template, event_Id=None):
        if not event_Id:
            event_Id = self._generate_hash_eventId(event_template)
        if self.optimized:
            start_token = event_template.split(' ')[0]
            if re.search(r'<.*?>', start_token):
                start_token = '<*>'
            self.template_match_dict[start_token][self._generate_template_regex(event_template)] = (event_Id, event_template)
        else:
            self.template_match_dict[self._generate_template_regex(event_template)] = (event_Id, event_template)

    def _generate_template_regex(self, template):
        template = re.sub(r'(<\*>\s?){2,}', '<*>', template)
        regex = re.sub(r'([^A-Za-z0-9])', r'\\\1', template)
        regex = regex.replace('\<\*\>', '(.*?)')
        regex = regex.replace('\<NUM\>', '(([\-|\+]?\d+)|(0[Xx][a-fA-F\d]+))')
        regex = regex.replace('\<IP\>', '((\d+\.){3}\d+)')
        regex = '^' + regex + '$'
        return regex

    def match_event(self, event_list):
        match_list = []
        paras = []
        if self.n_workers == 1:
            results = match_fn(event_list, self.template_match_dict, self.optimized)
        else:
            pool = mp.Pool(processes=self.n_workers)
            chunk_size = len(event_list) / self.n_workers + 1
            result_chunks = [pool.apply_async(match_fn, args=(event_list[i:i + chunk_size], self.template_match_dict, self.optimized))\
                             for i in xrange(0, len(event_list), chunk_size)]
            pool.close()
            pool.join()
            results = list(itertools.chain(*[result.get() for result in result_chunks]))
        for event, parameter_list in results:
            self.template_freq_dict[event] += 1
            paras.append(parameter_list)
            match_list.append(event)
        return match_list, paras

    def read_template_from_csv(self, template_filepath):
        template_dataframe = pd.read_csv(template_filepath)
        for idx, row in template_dataframe.iterrows():
            event_Id = row['EventId']
            event_template = row['EventTemplate']
            self.add_event_template(event_template, event_Id)


    def match(self, log_filepath, template_filepath):
        print('Processing log file: {}'.format(log_filepath))
        start_time = datetime.now()
        loader = logloader.LogLoader(self.logformat, self.n_workers)
        self.read_template_from_csv(template_filepath)
        log_dataframe = loader.load_to_dataframe(log_filepath)
        print('Matching event templates...')
        match_list, paras = self.match_event(log_dataframe['Content'].tolist())
        log_dataframe = pd.concat([log_dataframe, pd.DataFrame(match_list, columns=['EventId', 'EventTemplate'])], axis=1)
        log_dataframe['ParameterList'] = paras
        self._dump_match_result(os.path.basename(log_filepath), log_dataframe)
        match_rate = sum(log_dataframe['EventId'] != 'NONE') / float(len(log_dataframe))
        print('Matching done, matching rate: {:.1%} [Time taken: {!s}]'.format(match_rate, datetime.now() - start_time))
        return log_dataframe

    def _dump_match_result(self, log_filename, log_dataframe):
        log_dataframe.to_csv(os.path.join(self.outdir, log_filename + '_structured.csv'), index=False)
        template_freq_list = [[eventId, template, freq] for (eventId, template), freq in self.template_freq_dict.iteritems()]
        template_freq_df = pd.DataFrame(template_freq_list, columns=['EventId', 'EventTemplate', 'Occurrences'])
        template_freq_df.to_csv(os.path.join(self.outdir, log_filename + '_templates.csv'), index=False)

    def _generate_hash_eventId(self, template_str):
        return hashlib.md5(template_str.encode('utf-8')).hexdigest()[0:8]

    def _get_parameter_list(self, row):
        template_regex = re.sub(r'([^A-Za-z0-9])', r'\\\1', row["EventTemplate"])
        template_regex = "^" + template_regex.replace("\<\*\>", "(.*?)") + "$"
        parameter_list = re.findall(template_regex, row["Content"])
        parameter_list = parameter_list[0] if parameter_list else ()
        parameter_list = list(parameter_list) if isinstance(parameter_list, tuple) else [parameter_list]
        return parameter_list

def match_fn(event_list, template_match_dict, optimized=True):
    print("Worker {} start matching {} lines.".format(os.getpid(), len(event_list)))
    match_list = [regex_match(event_content, template_match_dict, optimized)
                  for event_content in event_list]
    return match_list

def regex_match(msg, template_match_dict, optimized):
    matched_event = None
    template_freq_dict = Counter()
    match_dict = template_match_dict
    parameter_list = []
    if optimized:
        start_token = msg.split(' ')[0]
        if start_token in template_match_dict:
            match_dict = template_match_dict[start_token]
            if len(match_dict) > 1:
                match_dict = OrderedDict(sorted(match_dict.items(), 
                     key=lambda x: (len(x[1][1]), -x[1][1].count('<*>')), reverse=True))
            for regex, event in match_dict.iteritems():
                parameter_list = re.findall(regex, msg.strip())
                if parameter_list:
                    matched_event = event
                    break    
    
    if not matched_event:
        if optimized:
            match_dict = template_match_dict['<*>']
        if len(match_dict) > 1:
            match_dict = OrderedDict(sorted(match_dict.items(), 
                 key=lambda x: (len(x[1][1]), -x[1][1].count('<*>')), reverse=True))
        for regex, event in match_dict.iteritems():
            parameter_list = re.findall(regex, msg.strip())
            if parameter_list:
                matched_event = event
                break    

    if not matched_event:
        matched_event = ('NONE', 'NONE')
    if parameter_list:
        parameter_list = list(parameter_list[0])
    return matched_event, parameter_list

