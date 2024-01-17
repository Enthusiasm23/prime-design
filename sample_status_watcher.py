#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : TopGen
@Time    : 2024/1/17 14:51
@Author  : lbfeng
@File    :  sample_status_watcher.py
"""
import sys
import primkit as pt
from primer_design import emit
from primer_design import check_email_sent
from primer_design import check_sample_system
from primer_design import get_audit_status
from primer_design import update_email_status

# 设置日志
logger = logging.getLogger(__name__)


def check_order(sampleID, primer_result):
    """
    Monitors and manages the process of checking sample audit status, sending emails, and updating database.

    :param sampleID: The unique identifier for the sample.
    :param primer_result: The file path of the primer result that will be attached to the email.
    """
    toaddrs = config['emails']['setup']['log_toaddrs']
    cc = config['emails']['setup']['log_cc']
    subject = f'样本引物合成订购 (自动发送) - {sampleID} '
    message = f'样本ID：{sampleID}\nCMS审核结果：已通过\n引物结果：{os.path.basename(primer_result)}（见附件）'

    email_status = check_email_sent(sampleID, 'monitor_order')

    if email_status == 0:
        sample_local = check_sample_system(sampleID)
        status_abbr, status_desc = get_audit_status(sampleID, sample_local)
        review_status = f'{status_abbr}({status_desc})'

        # 审核通过
        if status_abbr in ['YWC', 'YSH', 'BGYSH']:
            if send_email:
                emit(subject, message, attachments=[primer_result], to_addrs=toaddrs, cc_addrs=cc)
                update_email_status(sampleID, 'monitor_order', order_date, review_status)
            logger.info('Complete the sample primer design and send the order!')
            sys.exit(0)

        # 检测中
        elif status_abbr in ['JCZ', 'DSH', 'BGDSH']:
            subject = f'样本审核状态持续检测 - {sampleID}'
            message = f'样本ID {sampleID} 审核状态持续检测中···\n目前样本审核状态：{review_status}。\n注意：在订单发送之前，审核人员可查看附件的引物订单检查错误，并告知程序管理人员终止自动发送程序。\n提示：程序会按照自定义时间检测CMS系统审核状态，等待审核状态发生改变，该引物订单会自动发送订购。'
            emit(subject, message, attachments=[primer_result], to_addrs=toaddrs, cc_addrs=cc)
            logger.info('Sample primer design order is being sent automatically.')

        # 检测终止
        else:
            subject = f'样本状态检测异常警告 - {sampleID}'
            message = f'警告：样本ID {sampleID} 样本状态检测异常。\nCMS审核状态：{review_status}\n提示：程序将自动退出以防止进一步的数据处理。\n请立即检查相关数据并采取适当措施。'
            emit(subject, message, to_addrs=toaddrs, cc_addrs=cc)
            update_email_status(sampleID, 'monitor_order', order_date, review_status=review_status,
                                email_sent=2)
            logger.error(
                f'Sample ID {sampleID} Detect the anomaly and exit the program. Please check the relevant data immediately and take appropriate action.')
            sys.exit(1)

    elif email_status in [1, 2]:
        # 如果EmailSent是1或是2，不发送邮件
        logger.info(f"No action needed for SampleID: {sampleID} as EmailSent is {email_status}")
        sys.exit(0)

    else:
        # 如果EmailSent是None或其他值，发送错误消息并退出程序
        logger.error(f"Unexpected EmailSent status for SampleID: {sampleID}")
        sys.exit(1)


if __name__ == '__main__':
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Automatic primer design.')
    # 必需的参数
    parser.add_argument('-s', '--sample-id', required=True, dest='sampleID',
                        help='Sample ID for primer design.')
    parser.add_argument('-p', '--primer-result', required=True, dest='primer_result',
                        help='result for primer design.')
    args = parser.parse_args()
    check_order(args.sampleID, args.primer_result)
