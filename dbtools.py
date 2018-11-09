#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
from cmdblib.client import Client
import tablib
import ansible.runner
reload(sys)
sys.setdefaultencoding('utf-8')
# 对外MYSQL服务器地址1
#BASE_HOST=47.52.234.114
#BASE_PORT=3306
#BASE_DATABASE=elenet_data
#BASE_USERNAME=root
#BASE_PASSWORD=Eleme#123qwert
client = Client(host="cmdb.elenet.me",
                port=3306,
                client_id="87d4za2es2de52a1ebf387625fffe3",
                secret="你自己的")    # noqa
dept = u"北京研发中心"

def exec_ansible_shell(host, cmd):
    results = ansible.runner.Runner(pattern=host, forks=10,
                                    module_name='shell',
                                    module_args=cmd).run()
    if not results:
        return ''
    else:
        for (hostname, result) in results['contacted'].items():
            if 'failed' not in result:
                return result['stdout']
            else:
                return ''

def get_domain(host):
    if host.startswith('vpc'):
        host = host+".elenet.me"
        cmd = '''for i in `ls /opt/etc/nginx/sites-enabled/|grep -vE \
            "default*|status.ele*|*.bak"|sed "s/.conf//g"`;do echo $i|\
            tr "\n" " ";nslookup $i |awk '/^Address: / { print $2 }'|\
            tr "\n" " ";done'''
    else:
        cmd = '''for i in `ls /opt/nginx/conf/vhost.d/|grep -vE \
            "default*|status.ele*|*.bak"|sed "s/.conf//g"`;do echo $i|\
            tr "\n" " ";nslookup $i |awk '/^Address: / { print $2 }';done'''
    domains = exec_ansible_shell(host, cmd)
    return domains

def get_host_by_appid(appid):
    """根据appid获取host"""
    ghs = client.search_entities_by_query(
            "_type: rl_group_hosts AND app_id:{} \
            AND hosts:(xg* or vpc* or qc* or sh* or wg* or \
            al*)".format(appid), page=1, size=200)
    gh_info = [gh.__dict__ for gh in ghs]
    return sorted(gh_info, key=lambda k: (k['_env'], k['_hosts']))

def get_host_info(host):
    """获取主机信息"""
    host_info = client.search_entities_by_query("_type: server_logic AND \
                                         hostname: {}".format(host))
    hostname = host_info[0].hostname
    ip = host_info[0].nic0_ip
    mem = host_info[0].mem if host_info[0].mem\
        else ''
    cpu = host_info[0].cpu if host_info[0].cpu\
        else ''
    hd = host_info[0].hd if host_info[0].hd\
        else ''
    return hostname, ip, mem, cpu, hd

def main():
    """main"""
    data = tablib.Dataset()
    data.headers = (u'部门', u'项目', u'appid', u'app_name', u'app_type',
                    u'port', u'环境', u'分组', u'主机', u'主机ip',
                    u'服务器配置', u'域名及解析', u'dev_name')
    apps = client.search_entities('app', dept=dept, page=1, size=2000)
    app_info = [app.__dict__ for app in apps]
    all_apps = sorted(app_info,
                      key=lambda k: (k['_product_line'], k['_app_id']))
    for app in all_apps:
        product_line = app['_product_line']
        appid = app['_app_id']
        app_name = app['_app_name']
        app_type = app['_app_type']
        port = app['_port']
        dev_name = app['_dev_name']
        all_hosts = get_host_by_appid(appid)
        for info in all_hosts:
            env = info['_env']
            name = info['_name']
            for host in info['_hosts']:
                hostname, ip, mem, cpu, hd = get_host_info(host)
                if app_type == 'webresource' and 'web-web' not in host and\
                        'fe-static' not in host:
                    domains = get_domain(host)
                else:
                    domains = ''
                data.append((dept, product_line, appid, app_name, app_type,
                            port, env, name, hostname, ip,
                            mem+"G-"+cpu+"C-"+hd, domains, dev_name))
    with open('./bjdev_resource.csv', 'wb') as f:
        f.write(data.csv)

if __name__ == "__main__":
    main()

