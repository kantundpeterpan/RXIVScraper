#!/usr/bin/env python
# coding: utf-8

# In[3]:


from requests import get


# In[4]:


from bs4 import BeautifulSoup


# In[5]:


from multiprocessing import Pool


# In[6]:


import re


# In[7]:


import pandas as pd


# In[8]:


from tqdm.auto import tqdm
from p_tqdm import p_map


# In[9]:


import numpy as np


# In[10]:


import string


# In[21]:


import argparse


# **Important infos**
# 
# - Authors
# - Publication Date
# - Abstract

# In[17]:


# %%file medbiorxivScraper.py
class MedBioRxivScraper(object):
    
    base_url =  "https://www.medrxiv.org/search/"                "%s%%20jcode%%3Amedrxiv%%7C%%7Cbiorxiv%%20"                "numresults%%3A%s%%20sort%%3A%s%%20format_result%%3Astandard"
    
    
    
    sort = {
        'best':'relevance-rank',
        'new':'publication-date%20direction%3Adescending',
        'old':'publication-date%20direction%3Aascending'
    }
    
    doi_re = re.compile('https://doi\.org.*\d')
    remove_html_re = re.compile('<[^<]+?>')
    
    def search(self, 
                 search_term,
                 no_results=1000,
                 sort='best'
                 ):
        
        self.search_term = search_term
        self.url = self.base_url % (search_term.replace(' ', '%20'), no_results, self.sort[sort])
        print('Waiting for server response ...', end=' ')
        html = get(self.url).content
        print('Done.')
        print('Parsing HTML ...', end=' ')
        self.soup = BeautifulSoup(html, features='lxml')
        print('Done.')
        print('Extracting DOIs...')
        self.get_dois()
        if len(self.DOIs)==no_results:
            print('###! There might be more results available !###')
        
    def get_dois(self, regex = 'https://doi\.org.*\d'):
        
        self.DOIs = re.compile(regex).findall(self.soup.text)
        print('No. of results: ', len(self.DOIs))
        
        
    def parse(self, n_jobs=12):
        
        if n_jobs > len(self.DOIs):
            n_jobs = len(self.DOIs)
            
            
#        with Pool(processes=n_jobs) as pool:
 #           data = list(tqdm(
  #              pool.imap(
   #                 MedBioRxivScraper.parse_article,
    #                self.DOIs,
	#	    chunksize=len(self.DOIs)//n_jobs
         #       ),
          #      total = len(self.DOIs)
           # ))

        data = p_map(MedBioRxivScraper.parse_article, self.DOIs, num_cpus=n_jobs)
    
        self.data = pd.DataFrame(data, columns = ['authors', 'affiliations',
                                                  'title', 'pub_date', 'abstract', 'doi'])
        
        self.data.pub_date = pd.to_datetime(self.data.pub_date)
        
    
    @classmethod
    def parse_article(cls, doi):
        
        
        res = get(doi)
        temp_soup = BeautifulSoup(res.content, features='lxml')
        
        authors = temp_soup.find_all('meta', {'name':['citation_author']})
        authors = ';'.join([author['content'].strip(string.punctuation) for author in authors])
        
        affil = temp_soup.find_all('meta', {'name':['citation_author_institution']})
        affil = ';'.join(np.unique([aff['content'].strip(string.punctuation) for aff in affil]))

#         authors_string = ';'.join(['%s (%s)' % (x[0], x[1]) for x in zip(authors, affil)])
        
        try:
            pub_date = temp_soup.find_all('meta', {'name':'article:published_time'})[0]['content']
        except:
            pub_date = '1900-01-01'
        try:
            title = temp_soup.find_all('meta', {'name':'citation_title'})[0]['content']
        except:
            title = 'none'
        try:
            abstract = temp_soup.find_all('meta', {'name':'citation_abstract'})[0]['content']
            abstract = cls.remove_html_re.sub('', abstract)
        except:
            abstract = 'none'
        
        return authors, affil, title, pub_date, abstract, doi


# In[22]:


if __name__ == '__main__':
    
    def main():
    
        parser = argparse.ArgumentParser()

        parser.add_argument('-q', '--query', type=str, help='phrase for search query')
        parser.add_argument('-nr', '--no_results', type=int, help='max. number of results to retrieve')
        parser.add_argument('-p', '--processes',type=int, help='number of processes to use for parsing')
        parser.add_argument('-f', '--file', type=str, help='output file')
        parser.add_argument('-s', '--sort', type=str, help='Sort by best, old, new')

        args = parser.parse_args()

        if not args.query:
            print('###!  No query specified - Aborting !###')
            return

        s = MedBioRxivScraper()
        
        search_args = {
            'no_results':1000,
            'sort':'best'
        }
        
        for arg in ('no_results', 'sort'):
            if not getattr(args, arg) == None:
                search_args[arg] = getattr(args, arg)

        s.search(args.query, **search_args)

        if args.processes:
            s.parse(n_jobs=args.processes)
        else:
            s.parse()

        filename = 'output.csv'
        if args.file:
            filename = args.file

        s.data.to_csv(filename, index=False)

        print('### Finished')
        
        return
    
    main()


# In[106]:




