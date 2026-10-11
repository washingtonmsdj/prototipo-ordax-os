#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {resolve, relative, isAbsolute, sep, join, extname} from 'node:path';
import {runBrowser, sleep} from '../browser-proof/chromium.mjs';
const args=process.argv.slice(2);
if (args.some((value,index)=> index%2===0 && !['--bundle-dir','--evidence-dir'].includes(value))) throw Error('Unsupported argument');
const value=(key,fallback)=> args.includes(key) ? args[args.indexOf(key)+1] : fallback;
const bundle=resolve(value('--bundle-dir','out/web-client'));
const evidence=resolve(value('--evidence-dir','out/web-viewport-proof'));
const mime={'.js':'text/javascript','.css':'text/css','.html':'text/html','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2','.json':'application/json'};
const server=createServer(async(request,response)=>{
  try {
    const pathname=decodeURIComponent(new URL(request.url,'http://127.0.0.1').pathname);
    const path=resolve(bundle,'.'+(pathname==='/'?'/index.html':pathname));
    const rel=relative(bundle,path);
    if(rel==='..'||rel.startsWith('..'+sep)||isAbsolute(rel))throw Error('Outside bundle');
    const bytes=await readFile(path);
    response.writeHead(200,{'content-type':mime[extname(path)]??'application/octet-stream'});response.end(bytes);
  } catch {response.writeHead(404);response.end();}
});
await new Promise(done=>server.listen(0,'127.0.0.1',done));
const origin='http://127.0.0.1:'+server.address().port;
await mkdir(evidence,{recursive:true});
try {
 for (const path of ['/web2', '/web2/']) assert.equal((await fetch(origin + path)).status, 404, 'Retired test route must not serve the canonical client');
 const reports=await runBrowser(async client=>{
  async function evaluate(expression){
    const reply=await client.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(reply.exceptionDetails)throw Error(reply.exceptionDetails.exception?.description??'Evaluation failed');
    return reply.result?.value;
  }
  async function ready(){
    const deadline=Date.now()+15000;
    while(!await evaluate("!!document.querySelector('.web-workspace') && document.querySelector('#ordax-boot-screen').hidden")){
      if(Date.now()>deadline)throw Error('Canonical Web failed to mount');await sleep(50);
    }
    await evaluate('document.fonts.ready.then(()=>true)');
    await evaluate("Promise.all([...document.images].filter(img=>img.getClientRects().length>0).map(img=>img.decode().catch(()=>{throw Error('Asset failed: '+img.currentSrc)}))).then(()=>true)");
  }
  async function click(selector){
    const point=await evaluate("(()=>{const node=[...document.querySelectorAll("+JSON.stringify(selector)+")].find(node=>node.getClientRects().length>0);if(!node)throw Error('Missing control');node.scrollIntoView({block:'center',inline:'center',behavior:'instant'});const box=node.getBoundingClientRect();const x=box.left+box.width/2,y=box.top+box.height/2,hit=document.elementFromPoint(x,y);if(!box.width||!box.height||!node.contains(hit))return {obstructed:true,box:{x,y,width:box.width,height:box.height},hit:hit?.outerHTML.slice(0,400)};return {x,y};})()");
    if(point.obstructed){const shot=await client.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await writeFile(join(evidence,'failure.png'),Buffer.from(shot.data,'base64'));throw Error('Obstructed '+selector+': '+JSON.stringify(point));}
    await client.send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
    await client.send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
    await sleep(100);
  }
  const reports=[];
  for(const [width,height] of [[1440,900],[1024,768],[390,844],[320,568],[844,390]]){
    await client.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    for(const view of ['home','assistant','projects','spaces','apps','files','internet','store']){
      await client.send('Page.navigate',{url:origin+'/?view='+view});await ready();
      const state=await evaluate("({canonical:document.querySelectorAll('.web-workspace').length===1&&location.pathname==='/',noOverflow:document.documentElement.scrollWidth<=innerWidth,assets:[...document.images].filter(img=>img.getClientRects().length>0).every(img=>img.complete&&img.naturalWidth>0),font:document.fonts.check('14px Inter'),unavailable:document.querySelector('.web-sidebar-status')?.textContent.includes('não conectados')})");
      assert.ok(Object.values(state).every(Boolean),JSON.stringify({width,height,view,state}));
    }
    await client.send('Page.navigate',{url:origin+'/?view=home'});await ready();
    await click('[aria-label="Abrir aplicativos"]');
    assert.equal(await evaluate("!!document.querySelector('[role=dialog]')"),true);
    await client.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await client.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await sleep(100);
    const dialogDeadline=Date.now()+3000;
    while(await evaluate("!!document.querySelector('[role=dialog]')")){if(Date.now()>dialogDeadline)throw Error('Launcher did not close after Escape');await sleep(25);}
    if(width>760){
      await click('[aria-label="Abrir Studio pelo dock"]');await click('[aria-label="Maximizar Studio"]');
      assert.equal(await evaluate('!!document.querySelector(\'[aria-label="Janela Studio"].web-window-maximized\')'),true);
      await click('[aria-label="Minimizar Studio"]');await click('[aria-label="Abrir Studio pelo dock"]');
      assert.equal(await evaluate('!!document.querySelector(\'[aria-label="Janela Studio"].web-window-maximized\')'),true);
      await click('[aria-label="Fechar Studio"]');
      assert.equal(await evaluate('!document.querySelector(\'[aria-label="Janela Studio"]\')'),true);
      await click('[aria-label="Abrir Studio pelo dock"]');
      assert.equal(await evaluate('document.querySelectorAll(\'[aria-label="Janela Studio"]\').length'),1);
    }
    const shot=await client.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(join(evidence,'web-'+width+'x'+height+'.png'),Buffer.from(shot.data,'base64'));
    reports.push({width,height,views:8,assets:true,noOverflow:true,launcher:true,windowLifecycle:width>760});
  }
  return reports;
 });
 await writeFile(join(evidence,'report.json'),JSON.stringify(reports,null,2)+'\n');
 console.log('SURFACE_BROWSER_SMOKE=PASS '+JSON.stringify(reports));
}finally{await new Promise(done=>server.close(done));}
