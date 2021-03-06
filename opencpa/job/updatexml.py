# vim: set ts=4 sw=4 et: -*- coding: utf-8 -*-

import os, sys
sys.path.append(os.path.join(os.path.abspath('..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "opencpa.settings.local")

from datetime import datetime, timedelta, date
from django.db.models import Sum
from job.models import *
from job import myutil
import re 
import django
django.setup()

#xml_url = 'https://web3.dgpa.gov.tw/WANT03FRONT/AP/WANTF00003.aspx'
xml_url = 'https://web3.dgpa.gov.tw/WANT03FRONT/AP/WANTF00003.aspx?GETJOB=Y'

# ensure data in CurrentJob is up to date
twDate = (datetime.utcnow() + timedelta(hours=8)).date()
yesterday = twDate + timedelta(days=-1)
ur = UpdateRecord.objects.all()[0]

if (twDate != ur.last_update_day) or (not CurrentJob.objects.all()): # data is old or last update failed
    xml_jobs = myutil.getxml(xml_url)
    CurrentJob.objects.all().delete()
    JobTrend.objects.filter(date=yesterday).delete()
    for xml_job in xml_jobs:
        # filter unqualified sysnam
        sysname = xml_job['sysnam']
        if not myutil.filter(sysname):
            continue

        c_job = CurrentJob()
        c_job.title = xml_job['title']
        c_job.sysnam = sysname
        c_job.org_name = xml_job['org_name']
        c_job.person_kind = xml_job['person_kind']
        c_job.rank_from = int(xml_job['rank']['from'])
        c_job.rank_to = int(xml_job['rank']['to'])
        c_job.work_quality = xml_job['work_quality'] if xml_job['work_quality'] else 'no data'
        c_job.work_item = xml_job['work_item']
        c_job.work_addr = xml_job['work_addr'] if xml_job['work_addr'] else 'no data'
        
        # get the unique job_id of this job
        c_job.job, created = Job.objects.get_or_create(
            title = c_job.title,
            sysnam = c_job.sysnam,
            org_name = c_job.org_name,
            person_kind = c_job.person_kind,
            rank_from = c_job.rank_from,
            rank_to = c_job.rank_to,
            work_quality = c_job.work_quality,
            work_item = c_job.work_item,
            work_addr = c_job.work_addr
        )
        if created:
            job = Job.objects.get(id=c_job.job.id)
            job.is_resume_required = myutil.isResumeRequired(xml_job['view_url'].replace('http://', 'https://'))
            job.save()
        
        searchObj = re.search( r'(\d+)', xml_job['num'], re.M|re.I)
        if searchObj:
            c_job.num = int(searchObj.group())
        else:
            c_job.num = 0
            
        c_job.gender = xml_job['gender']
        c_job.work_places_id = xml_job['work_places'][0]
        c_job.date_from = xml_job['date_from']
        c_job.date_to = xml_job['date_to']
        c_job.is_handicap = xml_job['is_handicap']
        c_job.is_orig = xml_job['is_orig']
        c_job.is_local_orig = xml_job['is_local_orig']
        c_job.is_training = xml_job['is_training']
        c_job.job_type = xml_job['type']
        c_job.email = xml_job['email']
        c_job.work_quality = xml_job['work_quality'] if xml_job['work_quality'] else 'no data'
        c_job.contact = xml_job['contact']
        c_job.url = xml_job['url']
        c_job.view_url = xml_job['view_url'].replace('http://', 'https://')
        c_job.is_resume_required = Job.objects.get(id=c_job.job.id).is_resume_required
                
        if ( c_job.date_to <= (twDate + timedelta(days=2)) ):
            c_job.isExpiring = True
        else:
          c_job.isExpiring = False

        job_his, created = JobHistory.objects.get_or_create(
            job = c_job.job,
            date_from = c_job.date_from,
            date_to = c_job.date_to
        )
            
        c_job.history_count = JobHistory.objects.filter(job = c_job.job).count()
        c_job.save()

    # accumulate job trends
    level = [3, 2, 1]
    level_rank = [0, 6, 10, 14]
    for i in xrange(3):
        yesterdayJobs = CurrentJob.objects.filter(date_from=yesterday, rank_to__gte=level_rank[i], rank_to__lt=level_rank[i+1]).values('sysnam').annotate(num=Sum('num')).order_by('-num')
        for yjob in yesterdayJobs:
            jt = JobTrend(sysnam=yjob['sysnam'], date=yesterday, num=yjob['num'], level=level[i])
            jt.save()
    
    ur.last_update_day = twDate
    ur.save()
