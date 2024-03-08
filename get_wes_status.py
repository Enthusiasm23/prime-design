#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2024/1/8 15:51
@Author  : lbfeng
@File    :  get_wes_status.py
"""
import json
import logging
import sys
import requests
import argparse
import http_api

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s')

httpApi = http_api.HttpApi()

def doBack(info, path):
    global sid
    httpApi.backDesign(sid, info, path)

def doError(err):
    global sid
    logging.error(err)
    httpApi.backDesign(sid, err, '')

def get_cms_accessToken():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}
    postUrl = 'http://cms.topgen.com.cn/user/login/auth'
    postData = {'userName': 'bioinfo', 'password': 'Top50800383', 'rememberMe': '1'}
    try:
        response = requests.post(postUrl, params=postData, headers=headers)
        if response.status_code == 200:
            accessToken = json.loads(response.text)['data']['accessToken']
            logging.info(f'AccessToken obtained successfully, accessToken: {accessToken}')
            return accessToken
        else:
            doError('ERROR: response.status_code is not equal to 200.')
            sys.exit(1)
    except Exception as e:
        doError(f'ERROR: Error getting sample audit status of cms system. The specific reason is {e}')
        sys.exit(1)


def get_sample_status(sampleSn):
    """
    Retrieves the status of a sample based on the specified system type.

    :param sampleSn: The sample number to check the status for.
    :return: The status of the sample.
    """
    access_token = get_cms_accessToken()
    sample_info_url = 'http://cms.topgen.com.cn/sample/sample/search'
    payload = {'accessToken': access_token, "search[sampleSn][value]": sampleSn, "search[sampleSn][query]": "eq"}
    try:
        result = requests.get(sample_info_url, params=payload)
        dicts = json.loads(result.text)
        if len(dicts["data"]) > 0:
            sample_status = dicts["data"][0]["sampleStatusShow"]
            logging.info(f'Successfully obtained sampleStatus, sampleStatus: {sample_status}')
            return sample_status
        else:
            doError('ERROR: Sample ID does not exist in cms system!')
            sys.exit(1)
    except Exception as e:
        doError(
            f'ERROR: An error occurred while getting the item ID of the sample for the cms system. The specific reason is {e}')
        sys.exit(1)


def get_audit_status(sample_sn):
    """
    Retrieves the audit status for a given sample number.

    :param sample_sn: The sample number to check the status for.
    :return: A tuple containing the audit status code and its description.
    """
    status_dict = {
        'YCY': '已采样',
        'YSC': '已送出',
        'YSY': '已收样',
        'JCZ': '检测中',
        'FJZ': '复检中',
        'YWC': '已完成',
        'JCZZ': '检测终止',
        'BHG': '不合格',
        'BGDSH': '报告待审核',
        'BGWTG': '报告审核未通过',
        'BGYSH': '报告已审核',
        'BYZ': '补样中',
        'ZTJC': '暂停检测',
    }

    audit_status = get_sample_status(sample_sn)

    # For the OLD system, find the abbreviation from the status description
    status_abbr = next((abbr for abbr, desc in status_dict.items() if desc == audit_status), 'Unknown')
    status_desc = audit_status

    return status_abbr, status_desc


def execute(sample_ids):
    for sample_id in sample_ids:
        # 检查cms样本审核状态
        status_abbr, status_desc = get_audit_status(sample_id)
        print(f'{sample_id}\t{status_abbr}\t{status_desc}')


def main():
    parser = argparse.ArgumentParser(description='get wes check status',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('sample_ids', nargs='+',
                        help='Sample IDs, example: NGS221109-045 NGS221110-046')

    args = parser.parse_args()

    execute(args.sample_ids)


if __name__ == '__main__':
    main()
