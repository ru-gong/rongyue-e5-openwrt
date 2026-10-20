'use strict';
import { open, unlink } from 'fs';
return function(ctx) {
    function request(body) {
        let ts = clock(true);
        let path = `/tmp/run/e5-hotspot/request-${ts[0]}-${ts[1]}`;
        let file = open(path, 'w', 0600);
        if (!file) return {ok:false,error:'热点管理服务未就绪'};
        file.write(sprintf('%J', body)); file.close();
        let result = ctx.sh_json(`/usr/bin/python3 /etc/e5-infoscreen/plugins/hotspot/control.py rpc ${path}`);
        unlink(path);
        return result ?? {ok:false,error:'热点管理请求未完成'};
    }
    return {
        'GET /status': function(req) { return request({action:'status'}); },
        'POST /password': function(req) {
            let p=req.body?.password;
            if(type(p)!='string'||length(p)<8||length(p)>63||match(p,/[^ -~]/))
                return {ok:false,error:'密码需为 8–63 位可打印英文字符'};
            return request({action:'password',password:p});
        },
        'POST /device': function(req) {
            let a=req.body?.action,mac=req.body?.mac;
            if(index(['kick','block','unblock'],a)<0||type(mac)!='string'||!match(mac,/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/))
                return {ok:false,error:'无效设备操作'};
            return request({action:a,mac});
        }
    };
};
