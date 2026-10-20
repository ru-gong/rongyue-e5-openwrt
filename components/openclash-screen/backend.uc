'use strict';
return function(ctx) {
    const script = '/etc/e5-infoscreen/plugins/openclash/control.py';
    return {
        'GET /status': function(req) {
            return ctx.sh_json(`/usr/bin/python3 ${script} status`) ?? { ok: false, error: '状态读取失败' };
        },
        'POST /mode': function(req) {
            let mode = req.body?.mode;
            if (type(mode) != 'string' ||
                (mode != 'direct' && mode != 'gfw' && mode != 'mainland' && mode != 'global'))
                return { ok: false, error: '无效模式' };
            // Only one of the four literal strings above reaches the shell.
            return ctx.sh_json(`/usr/bin/python3 ${script} request ${mode}`) ?? { ok: false, error: '切换请求失败' };
        },
        'POST /node': function(req) {
            let id = req.body?.id;
            if (type(id) != 'string' || !match(id, /^[a-f0-9]{24}$/))
                return { ok: false, error: '无效节点' };
            return ctx.sh_json(`/usr/bin/python3 ${script} select-node ${id}`) ?? { ok: false, error: '节点切换请求失败' };
        },
        'POST /test': function(req) {
            return ctx.sh_json(`/usr/bin/python3 ${script} test-nodes`) ?? { ok: false, error: '延迟测试请求失败' };
        }
    };
};
