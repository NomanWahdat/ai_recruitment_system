/* Real-browser local workflow test. No npm browser dependency required.
   Requires Node 22+ and installed Edge/Chrome. BROWSER_BIN overrides discovery. */
const fs=require("node:fs");
const path=require("node:path");
const {spawn}=require("node:child_process");
const root=path.resolve(__dirname,"..");
const runtime=path.join(root,".runtime");
const screenshots=path.join(root,"docs/screenshots");
fs.mkdirSync(runtime,{recursive:true});fs.mkdirSync(screenshots,{recursive:true});
const base=process.env.DEMO_URL||"http://127.0.0.1:3000";
const apiBase=process.env.DEMO_API||"http://127.0.0.1:8000/api";
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const report={started_at:new Date().toISOString(),steps:[],screenshots:[],errors:[]};
let socket, browser, jobId, candidateIds=[];
const pending=new Map();let nextId=0;
function call(method,params={}) {
  return new Promise((resolve,reject)=>{
    const id=++nextId;const timeout=setTimeout(()=>{pending.delete(id);reject(new Error("CDP timeout: "+method));},30000);
    pending.set(id,message=>{clearTimeout(timeout);if(message.error)reject(new Error(JSON.stringify(message.error)));else resolve(message.result);});
    socket.send(JSON.stringify({id,method,params}));
  });
}
async function evaluate(expression) {
  const result=await call("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});
  if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
  return result.result.value;
}
async function wait(expression,label,timeout=45000) {
  const deadline=Date.now()+timeout;
  while(Date.now()<deadline){if(await evaluate(expression))return;await sleep(400);}
  throw new Error("Timed out: "+label);
}
async function click(text,scope="document") {
  const ok=await evaluate(`(()=>{const el=Array.from(${scope}.querySelectorAll("button")).find(b=>b.textContent.trim()===${JSON.stringify(text)});if(!el)return false;el.click();return true;})()`);
  if(!ok)throw new Error("Button missing: "+text);
}
async function fill(selector,text,index=0) {
  const ok=await evaluate(`(()=>{const el=document.querySelectorAll(${JSON.stringify(selector)})[${index}];if(!el)return false;el.focus();el.select?.();return true;})()`);
  if(!ok)throw new Error("Input missing: "+selector);
  await call("Input.insertText",{text:String(text)});
}
async function select(selector,value,index=0) {
  await evaluate(`(()=>{const el=document.querySelectorAll(${JSON.stringify(selector)})[${index}];el.value=${JSON.stringify(String(value))};el.dispatchEvent(new Event("change",{bubbles:true}));})()`);
}
async function go(route){await call("Page.navigate",{url:base+route});await wait("document.readyState==='complete'","page ready");await sleep(500);}
async function shot(name,clip) {
  const image=await call("Page.captureScreenshot",{format:"png",captureBeyondViewport:!!clip,...(clip?{clip}:{})});
  fs.writeFileSync(path.join(screenshots,name+".png"),Buffer.from(image.data,"base64"));
  report.screenshots.push(name+".png");
}
async function api(route,method="GET",data) {
  return evaluate(`(async()=>{const token=document.cookie.split("; ").find(s=>s.startsWith("csrftoken="))?.split("=")[1];const response=await fetch(${JSON.stringify(apiBase+route)},{method:${JSON.stringify(method)},credentials:"include",headers:{"Content-Type":"application/json",...(token?{"X-CSRFToken":decodeURIComponent(token)}:{})},${data===undefined?"":"body:JSON.stringify("+JSON.stringify(data)+"),"}});return {status:response.status,data:response.status===204?null:await response.json()};})()`);
}
function passed(step){report.steps.push(step);console.log("PASS:",step);}
async function verifyAI() {
  await go("/ai-tools");await wait('document.body.innerText.includes("Job Parser")',"AI tools");
  const aiStatus=await api("/ai/status/");
  if(aiStatus.data.available)throw new Error("This offline browser regression requires providers disabled or keys absent.");
  await wait('document.body.innerText.includes("AI is unavailable")',"AI configuration message");
  if(!await evaluate('Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Test AI connection")?.disabled'))throw new Error("Unconfigured connection test should be disabled");
  const aiCheck=await api("/ai/check/","POST",{});
  if(aiCheck.data.ok||!aiCheck.data.fallback_reason)throw new Error("Missing-provider test must explain why AI is unavailable");
  await fill("textarea","Python Django PostgreSQL developer, 2 years experience");await click("Parse Job");await wait('document.body.innerText.includes("Local rubric")',"truthful local AI fallback");
  await wait('document.body.innerText.includes("No API key is configured") || document.body.innerText.includes("provider is disabled")',"actionable local fallback reason");
  passed("AI configuration, synthetic connection check and local responses explain missing/disabled providers");
  const aiHeight=await evaluate("document.documentElement.scrollHeight");
  await shot("08-ai-tools",{x:0,y:0,width:1440,height:aiHeight,scale:1});
}
async function verifyLiveAI() {
  await go("/ai-tools");await wait('document.body.innerText.includes("Job Parser")',"AI tools");
  const status=await api("/ai/status/");
  if(!status.data.available)throw new Error("A configured provider is required for the live browser check.");
  await wait('!Array.from(document.querySelectorAll("button")).find(b=>b.textContent.trim()==="Test AI connection")?.disabled',"configured provider");
  await click("Test AI connection");await wait('document.body.innerText.includes("AI connection verified.")',"live provider connection");
  await fill("textarea","Synthetic test: Python Django PostgreSQL backend developer with 2 years experience.");
  await click("Parse Job");
  await wait('Array.from(document.querySelectorAll("section")).find(s=>s.innerText.includes("Job Parser"))?.innerText.includes("Groq AI")',"live Groq job parse");
  const candidates=await api("/candidates/?search=kate");const jobs=await api("/jobs/?search=Backend%20Engineer");
  const candidate=candidates.data.results.find(c=>c.full_name==="Kate Example");
  const job=jobs.data.results.find(j=>j.title==="Backend Engineer");
  if(!candidate||!job)throw new Error("The synthetic demo fixtures are required for this live test.");
  await select("select",candidate.id,0);await select("select",job.id,1);
  await select("select",candidate.id,2);await select("select",job.id,3);
  await click("Explain Match");
  await wait('Array.from(document.querySelectorAll("section")).find(s=>s.innerText.includes("Match Explainer"))?.innerText.includes("Groq AI")',"live Groq match explanation");
  await click("Generate Questions");
  await wait('Array.from(document.querySelectorAll("section")).find(s=>s.innerText.includes("Interview Generator"))?.innerText.includes("Groq AI")',"live Groq interview questions");
  const height=await evaluate("document.documentElement.scrollHeight");
  await shot("12-groq-ai-verified",{x:0,y:0,width:1440,height:height,scale:1});
  passed("Live Groq connection, job parsing, match explanation and interview questions render in the browser using synthetic fixtures");
}
async function verifyEvidence() {
  const downloads=fs.mkdtempSync(path.join(runtime,"audit-download-"));
  await call("Browser.setDownloadBehavior",{behavior:"allow",downloadPath:downloads});
  await go("/evaluation");await wait('document.body.innerText.includes("Accuracy evaluation")',"evaluation page");
  const benchmark=await api("/evaluation/");
  if(benchmark.status!==200||benchmark.data.records!==24||!benchmark.data.failure_cases.length)throw new Error("Bundled evaluation report is missing or incomplete");
  await click("Download evaluation report");
  for(let i=0;i<40&&!fs.existsSync(path.join(downloads,"evaluation-report.json"));i++)await sleep(100);
  const exportedReport=JSON.parse(fs.readFileSync(path.join(downloads,"evaluation-report.json"),"utf8"));
  if(exportedReport.dataset_sha256!==benchmark.data.dataset_sha256)throw new Error("Evaluation download does not match the API report");
  await select('select[aria-label="Evaluation split"]',"challenge");
  await wait('document.body.innerText.includes("69.8%") && document.body.innerText.includes("negated-skills")',"measured challenge failures");
  const evalHeight=await evaluate("document.documentElement.scrollHeight");
  await shot("13-accuracy-evaluation",{x:0,y:0,width:1440,height:evalHeight,scale:1});
  await select('select[aria-label="Evaluation split"]',"regression");
  await wait('document.body.innerText.includes("No extraction errors measured in this split.")',"regression split");
  passed("Evaluation renders separate measured splits, honest failure cases and a matching downloadable report");
  const candidates=await api("/candidates/?search=kate");const jobs=await api("/jobs/?search=Backend%20Engineer");
  const candidate=candidates.data.results.find(c=>c.full_name==="Kate Example");
  const job=jobs.data.results.find(j=>j.title==="Backend Engineer");
  if(!candidate||!job)throw new Error("Synthetic seed_demo fixtures are required");
  await go("/candidates/"+candidate.id);await wait('document.body.innerText.includes("Job-specific comparison")',"candidate scoring");
  await select('select[aria-label="Select job"]',job.id);
  let before=await api("/analyses/?candidate="+candidate.id+"&job="+job.id);
  let previous=before.data.results[0]?.scoring_snapshot?.sha256;
  for(let pass=0;pass<2;pass++){
    await click("Run matching");
    let current;
    for(let i=0;i<80;i++){
      const response=await api("/analyses/?candidate="+candidate.id+"&job="+job.id);
      current=response.data.results[0];
      if(current?.scoring_snapshot?.sha256&&current.scoring_snapshot.sha256!==previous)break;
      await sleep(300);
    }
    if(!current?.scoring_snapshot?.sha256||current.scoring_snapshot.sha256===previous)throw new Error("Matching did not persist a new snapshot");
    previous=current.scoring_snapshot.sha256;
    await sleep(400);
  }
  const analyses=await api("/analyses/?candidate="+candidate.id+"&job="+job.id);
  const analysis=analyses.data.results[0];
  const scope='Array.from(document.querySelectorAll("article")).find(a=>a.querySelector("p")?.innerText.startsWith('+JSON.stringify("Job #"+job.id+" ")+'))';
  await wait(scope+'?.innerText.includes("Verify saved score")',"saved score controls");
  await wait(scope+'?.textContent.includes('+JSON.stringify(analysis.scoring_snapshot.sha256)+')',"latest displayed snapshot");
  await click("Verify saved score",scope);
  await wait(scope+'?.innerText.includes("Verified: reproduced")',"arithmetic replay");
  const verified=await api("/analyses/"+analysis.id+"/reproduce/");
  if(!verified.data.verified||verified.data.external_requests!==0)throw new Error("Saved arithmetic did not verify without provider calls");
  await click("Show score history",scope);
  const runs=await api("/score-runs/?analysis="+analysis.id);
  if(runs.data.count<2)throw new Error("Earlier scoring runs were overwritten");
  await wait(scope+'?.innerText.includes("Verify run #")',"historical score rows");
  await click("Download score snapshot",scope);
  const snapshotPath=path.join(downloads,"score-"+analysis.id+".json");
  for(let i=0;i<40&&!fs.existsSync(snapshotPath);i++)await sleep(100);
  const downloaded=JSON.parse(fs.readFileSync(snapshotPath,"utf8"));
  if(downloaded.sha256!==analysis.scoring_snapshot.sha256)throw new Error("Snapshot download differs from the saved calculation");
  const clip=await evaluate('(()=>{const el='+scope+';el.scrollIntoView({block:"start"});const r=el.getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:r.height,scale:1};})()');
  await shot("14-reproducible-scoring",clip);
  passed("Matching appends snapshots; current arithmetic verifies with zero AI calls; history and JSON download preserve the saved run");
}
async function main() {
  const locations=process.platform==="win32"?["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe","C:/Program Files/Google/Chrome/Application/chrome.exe"]:["/usr/bin/google-chrome","/usr/bin/chromium","/usr/bin/chromium-browser"];
  const executable=process.env.BROWSER_BIN||locations.find(p=>fs.existsSync(p));
  if(!executable)throw new Error("Install Chrome/Edge or set BROWSER_BIN.");
  const port=9300+Math.floor(Math.random()*500);
  const profile=fs.mkdtempSync(path.join(runtime,"browser-"));
  const logfile=fs.openSync(path.join(runtime,"browser.log"),"a");
  const args=["--headless","--disable-gpu","--no-first-run","--remote-debugging-port="+port,"--user-data-dir="+profile,"about:blank"];
  if(process.env.CI)args.push("--no-sandbox");
  browser=spawn(executable,args,{windowsHide:true,stdio:["ignore",logfile,logfile]});
  let ready=false;
  for(let i=0;i<80;i++){try{await fetch("http://127.0.0.1:"+port+"/json/version");ready=true;break;}catch{await sleep(250);}}
  if(!ready)throw new Error("Browser did not start; inspect .runtime/browser.log.");
  const page=await(await fetch("http://127.0.0.1:"+port+"/json/new?"+encodeURIComponent(base),{method:"PUT"})).json();
  socket=new WebSocket(page.webSocketDebuggerUrl);
  socket.addEventListener("message",event=>{const message=JSON.parse(event.data);if(message.id&&pending.has(message.id)){pending.get(message.id)(message);pending.delete(message.id);}
    if(message.method==="Runtime.exceptionThrown")report.errors.push(message.params.exceptionDetails.text);});
  await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true});});
  await call("Page.enable");await call("Runtime.enable");
  await call("Emulation.setDeviceMetricsOverride",{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await wait('document.body.innerText.includes("Welcome back")',"sign-in");
  await shot("01-sign-in");
  await fill('input[type="text"]',process.env.DEMO_USERNAME||"portfolio_demo");
  await fill('input[type="password"]',process.env.DEMO_PASSWORD||"PortfolioDemo!2026");
  await click("Sign In");
  await wait('document.body.innerText.includes("Evidence before decisions")',"authenticated dashboard");
  passed("Sign-in form establishes an HttpOnly session and loads dashboard data");await shot("02-dashboard");
  const cookieInfo=await call("Network.getCookies",{urls:[apiBase]});
  if(!cookieInfo.cookies.some(c=>c.name==="sessionid"&&c.httpOnly))throw new Error("Session cookie is not HttpOnly");
  if(process.env.EVIDENCE_ONLY){
    await verifyEvidence();
    if(report.errors.length)throw new Error("Browser JavaScript exceptions: "+report.errors.join(", "));
    return;
  }
  if(process.env.AI_ONLY){
    if(process.env.LIVE_AI)await verifyLiveAI();else await verifyAI();
    if(report.errors.length)throw new Error("Browser JavaScript exceptions: "+report.errors.join(", "));
    return;
  }
  const oldCandidates=await api("/candidates/?search=riley");
  for(const row of oldCandidates.data.results||[])if(row.email==="riley@example.com")await api("/candidates/"+row.id+"/","DELETE");
  const oldFailures=await api("/candidates/?processing_status=failed");
  for(const row of oldFailures.data.results||[])if(row.full_name==="unreadable")await api("/candidates/"+row.id+"/","DELETE");
  const oldJobs=await api("/jobs/?search=E2E");
  for(const row of oldJobs.data.results||[])if(row.title.startsWith("E2E E2E Backend"))await api("/jobs/"+row.id+"/","DELETE");
  const title="E2E Backend "+Date.now();
  await go("/jobs");await wait('document.body.innerText.includes("Create Job")',"jobs");
  await click("Create Job");await wait("!!document.querySelector('[role=\"dialog\"]')","job dialog");
  for(const [index,value] of ["E2E "+title,"Synthetic Research Lab","Remote","2","Python, Django, PostgreSQL","Bachelor of Computer Science"].entries())await fill('[role="dialog"] input',value,index);
  await fill('[role="dialog"] textarea',"Build reliable Python and Django services with PostgreSQL.");
  await evaluate("document.querySelector('[role=\"dialog\"] button[type=\"submit\"]').click()");
  await wait("!document.querySelector('[role=\"dialog\"]')","job saved");
  const jobs=await api("/jobs/?search="+encodeURIComponent(title));jobId=jobs.data.results[0]?.id;
  if(!jobId)throw new Error("Created job was not persisted");
  passed("Job creation form persists owned requirements");await shot("03-jobs");
  await go("/candidates");await wait('document.body.innerText.includes("Upload CVs")',"candidate list");
  await click("Upload CVs");await wait("!!document.querySelector('input[type=\"file\"]')","upload dialog");
  const documentNode=await call("DOM.getDocument");const fileNode=await call("DOM.querySelector",{nodeId:documentNode.root.nodeId,selector:'input[type="file"]'});
  await call("DOM.setFileInputFiles",{nodeId:fileNode.nodeId,files:[path.join(root,"evaluation/fixtures/sample-cv.docx"),path.join(root,"evaluation/fixtures/unreadable.pdf")]});
  await click("Queue extraction");await wait("!document.querySelector('[role=\"dialog\"]')","bulk upload accepted");
  let candidate;
  for(let i=0;i<100;i++){const response=await api("/candidates/?search=riley");candidate=response.data.results?.find(c=>c.email==="riley@example.com"&&c.processing_status==="completed");if(candidate)break;await sleep(500);}
  if(!candidate)throw new Error("Worker did not extract uploaded DOCX");
  candidateIds.push(candidate.id);
  let blank;
  for(let i=0;i<100;i++){const failed=await api("/candidates/?processing_status=failed");blank=failed.data.results.find(c=>c.full_name==="unreadable");if(blank)break;await sleep(500);}
  if(blank)candidateIds.push(blank.id);
  if(!blank)throw new Error("Blank PDF did not produce a visible failure");
  passed("Bulk upload queues real files; worker extracts DOCX and reports unreadable PDF failure");await shot("04-candidates");
  await go("/candidates/"+candidate.id);await wait('document.body.innerText.includes("Extracted profile and evidence")',"candidate evidence");
  await click("Review / correct profile");await wait("!!document.querySelector('[role=\"dialog\"]')","profile editor");
  await fill('[role="dialog"] input',"Python, Django, PostgreSQL",3);
  await click("Save reviewed profile");
  await wait("!document.querySelector('[role=\"dialog\"]')","profile saved");
  await wait('document.body.innerText.includes("Human-reviewed profile")',"reviewed profile rendered");
  await select('select[aria-label="Select job"]',jobId);await click("Run matching");
  await wait('document.body.innerText.includes("Job #'+jobId+'")',"fresh match");
  const verified=await api("/candidates/"+candidate.id+"/");
  if(!verified.data.profile_reviewed_at||!verified.data.skills.includes("PostgreSQL"))throw new Error("Profile correction was not saved");
  passed("Recruiter corrects evidence and matching records the revised profile");await shot("05-candidate-evidence");
  await click("Create application");await wait("document.querySelectorAll('select[aria-label=\"Next application stage\"]').length>0","application created");
  await select('select[aria-label="Next application stage"]',"review");await fill('input[aria-label="Human review note"]',"Checked source table and normalized Postgres to PostgreSQL before deciding.");await click("Record decision");
  await wait("Array.from(document.querySelectorAll(\"h4\")).some(el=>el.textContent.endsWith(\" review\"))","review stage");
  await select('select[aria-label="Next application stage"]',"shortlisted");await fill('input[aria-label="Human review note"]',"Verified Python, Django and PostgreSQL evidence against this role.");await click("Record decision");
  await wait("Array.from(document.querySelectorAll(\"h4\")).some(el=>el.textContent.endsWith(\" shortlisted\"))","human shortlist");
  const applications=await api("/applications/?candidate="+candidate.id);
  if(applications.data.results[0]?.decisions.length!==2)throw new Error("Decision history was not persisted");
  passed("Human review transitions applied -> review -> shortlisted with durable notes");
  await evaluate('Array.from(document.querySelectorAll("h3")).find(el=>el.textContent==="Human review and applications").scrollIntoView({block:"start"})');
  await evaluate('Array.from(document.querySelectorAll("details")).filter(el=>el.querySelector("summary")?.textContent.includes("Decision history")).forEach(el=>el.open=true)');
  const reviewClip=await evaluate('(()=>{const el=Array.from(document.querySelectorAll("h3")).find(el=>el.textContent==="Human review and applications").closest("section");const r=el.getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:r.height,scale:1};})()');
  await shot("06-human-review",reviewClip);
  await go("/rankings?job="+jobId);await wait('document.body.innerText.includes("Riley Example")',"ranking");await shot("07-rankings");
  await verifyAI();
  await verifyEvidence();
  await go("/automation");await wait('document.body.innerText.includes("Document extraction failed.")',"persistent failure task");await shot("09-automation-failure");
  await go("/candidates/"+blank.id);await wait('document.body.innerText.includes("Scanned/image-only")',"failure explanation");await shot("10-unreadable-resume");
  await call("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await go("/");await wait('document.body.innerText.includes("Evidence before decisions")',"mobile dashboard");
  if(!await evaluate("!!document.querySelector('nav[aria-label=\"Mobile navigation\"]')"))throw new Error("Mobile navigation missing");
  await shot("11-mobile-dashboard");passed("Mobile navigation is available");
  if(report.errors.length)throw new Error("Browser JavaScript exceptions: "+report.errors.join(", "));
}
(async()=>{
  let failure;
  try{await main();report.passed=true;}catch(error){failure=error;report.passed=false;report.failure=error.message;console.error(error.message);if(socket)try{await shot("failure");}catch{}}
  finally{
    if(socket){
      if(!process.env.KEEP_E2E_DATA||failure)try{for(const id of candidateIds)await api("/candidates/"+id+"/","DELETE");if(jobId)await api("/jobs/"+jobId+"/","DELETE");}catch{}
      try{await call("Browser.close");}catch{}socket.close();
    }
    report.finished_at=new Date().toISOString();fs.writeFileSync(path.join(root,process.env.EVIDENCE_ONLY?"docs/verification-scoring-evaluation-browser.json":process.env.AI_ONLY?(process.env.LIVE_AI?"docs/verification-ai-live-browser.json":"docs/verification-ai-browser.json"):"docs/verification-browser.json"),JSON.stringify(report,null,2)+"\n");
  }
  if(failure)process.exit(1);
})().catch(error=>{console.error(error);process.exit(1);});
