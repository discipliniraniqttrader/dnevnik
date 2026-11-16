const { chromium } = require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const srv=http.createServer((q,res)=>{const p=path.join(__dirname,decodeURIComponent(q.url.split('?')[0]));if(!fs.existsSync(p)){res.writeHead(404);return res.end()}res.writeHead(200,{'Content-Type':p.endsWith('.html')?'text/html':'text/javascript'});fs.createReadStream(p).pipe(res)});
(async()=>{await new Promise(r=>srv.listen(0,r));const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
for(const w of [720,1080]){const pg=await b.newPage();pg.on('pageerror',e=>console.log(e.message));await pg.goto(`http://127.0.0.1:${srv.address().port}/dtest.html?w=${w}`);await pg.waitForFunction('window.READY===true');
const ts=[];for(let i=0;i<4;i++)ts.push(await pg.evaluate('go()'));console.log(w,ts.map(x=>x.toFixed(0)).join(' '));await pg.close();}
await b.close();srv.close()})();
