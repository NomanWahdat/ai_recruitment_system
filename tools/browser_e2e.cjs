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
let fixtureCandidateId;
const focused=process.env.EVIDENCE_ONLY||process.env.AI_ONLY;
const isolatedUsername="ui_check_"+Date.now();
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

async function expand(text,scope="document") {
  const ok=await evaluate(`(()=>{const summary=Array.from(${scope}.querySelectorAll("summary")).find(el=>el.textContent.trim().startsWith(${JSON.stringify(text)}));if(!summary)return false;if(!summary.parentElement.open)summary.click();return true;})()`);
  if(!ok)throw new Error("Details missing: "+text);
}
async function fillLabel(text,value,scope='document.querySelector(\'[role="dialog"]\')') {
  const result=await evaluate(`(()=>{const label=Array.from(${scope}.querySelectorAll("label")).find(el=>el.textContent.trim().startsWith(${JSON.stringify(text)}));const input=label?.querySelector("input,textarea");if(!input)return null;input.dataset.e2eField="active";return true;})()`);
  if(!result)throw new Error("Field missing: "+text);
  await fill('[data-e2e-field="active"]',value);
  await evaluate('document.querySelector(\'[data-e2e-field="active"]\').removeAttribute("data-e2e-field")');
}
async function uploadFiles(files) {
  const documentNode=await call("DOM.getDocument");const input=await call("DOM.querySelector",{nodeId:documentNode.root.nodeId,selector:'[role="dialog"] input[type="file"]'});
  await call("DOM.setFileInputFiles",{nodeId:input.nodeId,files});
  await click("Upload and read resumes",'document.querySelector(\'[role="dialog"]\')');
  await wait("!document.querySelector('[role=\"dialog\"]')","upload complete");
}
async function verifyNavigation() {
  const links=await evaluate('Array.from(document.querySelectorAll(\'nav[aria-label="Main navigation"] a\')).map(a=>a.getAttribute("href"))');
  if(JSON.stringify(links)!==JSON.stringify(["/","/jobs","/candidates"]))throw new Error("Primary navigation is not limited to the hiring workflow");
  await go("/settings");await wait('document.body.innerText.includes("Settings & tools")',"settings");
  for(const route of ["/automation","/ai-tools","/rankings","/evaluation"]){if(!await evaluate('!!document.querySelector('+JSON.stringify('a[href="'+route+'"]')+')'))throw new Error("Tool is no longer accessible: "+route);}
  await shot("16-settings-tools");passed("Simple main navigation retains every advanced tool through Settings & tools");
}
async function fixturePair() {
  if(fixtureCandidateId&&jobId)return {candidate:fixtureCandidateId,job:jobId};
  const candidates=await api("/candidates/?search=kate");const jobs=await api("/jobs/?search=Backend%20Engineer");
  const candidate=candidates.data.results.find(c=>c.full_name==="Kate Example");const job=jobs.data.results.find(j=>j.title==="Backend Engineer");
  if(!candidate||!job)throw new Error("Synthetic seed_demo fixtures are required in focused mode");
  return {candidate:candidate.id,job:job.id};
}
async function verifyAssistant() {
  const pair=await fixturePair();
  await go("/ai-tools");await wait('document.body.innerText.includes("Job Parser")',"standalone assistant");
  await expand("Connection settings and diagnostics");
  const status=await api("/ai/status/");
  if(status.data.available && process.env.AI_ONLY && !process.env.LIVE_AI)throw new Error("Set LIVE_AI=1 for explicit focused live provider checks, or use an offline test server.");
  if(status.data.available){await click("Test AI connection");await wait('document.body.innerText.includes("AI connection verified.")',"provider connection");}
  else{const check=await api("/ai/check/","POST",{});if(check.data.ok||!check.data.fallback_reason)throw new Error("Offline fallback has no explanation");}
  await fill("textarea","Synthetic backend role requiring Python and Django.");await click("Parse Job");
  await wait('document.body.innerText.includes("Suggested requirements") || Array.from(document.querySelectorAll("section")).find(s=>s.innerText.includes("Job Parser"))?.innerText.includes("Skills:")',"readable job result");
  for(const [label,value] of [["Candidate for explanation",pair.candidate],["Job for explanation",pair.job],["Candidate for interview",pair.candidate],["Job for interview",pair.job]])await select('select[aria-label="'+label+'"]',value);
  await click("Explain Match");await wait('!document.body.innerText.includes("No explanation generated yet.")',"standalone explanation");
  await click("Generate Questions");await wait('Array.from(document.querySelectorAll("section")).find(s=>s.innerText.includes("Interview Generator"))?.querySelectorAll("li").length>0',"standalone interview questions");
  const source=status.data.available?"AI-assisted":"Standard matching";
  await wait('document.body.innerText.includes('+JSON.stringify(source)+')',"truthful source labels");
  await shot(status.data.available?"12-groq-ai-verified":"08-ai-tools");passed("Standalone AI tools, connection diagnostics and truthful AI/standard source labels remain available");
}
async function verifyEvidence() {
  const downloads=fs.mkdtempSync(path.join(runtime,"audit-download-"));await call("Browser.setDownloadBehavior",{behavior:"allow",downloadPath:downloads});
  await go("/evaluation");await wait('document.body.innerText.includes("System testing")',"evaluation summary");
  const benchmark=await api("/evaluation/");if(benchmark.status!==200||benchmark.data.records!==24)throw new Error("Benchmark unavailable");
  await click("Download readable summary");const summaryPath=path.join(downloads,"recruitment-software-test-summary.html");
  for(let i=0;i<50&&!fs.existsSync(summaryPath);i++)await sleep(100);
  const html=fs.readFileSync(summaryPath,"utf8");if(!html.includes("not a candidate assessment")||!html.includes("24"))throw new Error("Readable summary is missing context");
  await call("Page.navigate",{url:require("node:url").pathToFileURL(summaryPath).href});await wait('document.body.innerText.includes("What our resume-reading tests found")',"readable downloaded report");await shot("17-readable-evaluation-summary");
  await go("/evaluation");await wait('document.body.innerText.includes("System testing")',"testing page");await expand("Technical benchmark data and metrics");
  await click("Download technical data (JSON)");const reportPath=path.join(downloads,"evaluation-report.json");
  for(let i=0;i<50&&!fs.existsSync(reportPath);i++)await sleep(100);
  if(JSON.parse(fs.readFileSync(reportPath,"utf8")).dataset_sha256!==benchmark.data.dataset_sha256)throw new Error("Technical export mismatch");
  await select('select[aria-label="Evaluation split"]',"challenge");await wait('document.body.innerText.includes("69.8%")',"challenge metrics");await shot("13-accuracy-evaluation");
  await select('select[aria-label="Evaluation split"]',"regression");await wait('document.body.innerText.includes("No extraction errors measured in this split.")',"regression metrics");
  passed("Evaluation provides a readable HTML download while retaining full JSON, split metrics and failure cases");
  const pair=await fixturePair();await go("/candidates/"+pair.candidate+"?job="+pair.job+"&section=match");await wait('document.body.innerText.includes("Compare candidate")',"candidate comparison");
  let previous=(await api("/analyses/?candidate="+pair.candidate+"&job="+pair.job)).data.results[0]?.scoring_snapshot?.sha256;
  for(let pass=0;pass<2;pass++){
    await click("Compare candidate");let current;
    for(let i=0;i<100;i++){current=(await api("/analyses/?candidate="+pair.candidate+"&job="+pair.job)).data.results[0];if(current?.scoring_snapshot?.sha256&&current.scoring_snapshot.sha256!==previous)break;await sleep(300);}
    if(!current?.scoring_snapshot?.sha256||current.scoring_snapshot.sha256===previous)throw new Error("A score run was not saved");previous=current.scoring_snapshot.sha256;
    await wait('!Array.from(document.querySelectorAll("button")).find(b=>b.textContent.includes("Comparing this candidate"))',"comparison finished");
  }
  const analysis=(await api("/analyses/?candidate="+pair.candidate+"&job="+pair.job)).data.results[0];
  const scope='document.querySelector('+JSON.stringify('[data-analysis-id="'+analysis.id+'"]')+')';
  await wait(scope+'?.textContent.includes('+JSON.stringify(analysis.scoring_snapshot.sha256)+')',"latest score");await expand("How this score was calculated",scope);await click("Verify saved score",scope);await wait(scope+'?.innerText.includes("Verified: reproduced")',"score verification");
  const verification=await api("/analyses/"+analysis.id+"/reproduce/");if(!verification.data.verified||verification.data.external_requests!==0)throw new Error("Arithmetic replay failed");
  await click("Show previous comparisons",scope);await wait(scope+'?.innerText.includes("Verify run #")',"score history");await click("Download technical score data (JSON)",scope);
  const snapshotPath=path.join(downloads,"score-"+analysis.id+".json");for(let i=0;i<50&&!fs.existsSync(snapshotPath);i++)await sleep(100);
  if(JSON.parse(fs.readFileSync(snapshotPath,"utf8")).sha256!==analysis.scoring_snapshot.sha256)throw new Error("Snapshot export mismatch");
  const clip=await evaluate('(()=>{const r='+scope+'.getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:r.height,scale:1};})()');await shot("14-reproducible-scoring",clip);
  passed("Expandable score details preserve verification with zero AI calls, previous comparisons and exact JSON export");
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
  if(focused){
    await fill('input[type="text"]',process.env.DEMO_USERNAME||"portfolio_demo");await fill('input[type="password"]',process.env.DEMO_PASSWORD||"PortfolioDemo!2026");await click("Sign In");
  }else{
    await click("Create an account");await wait('document.body.innerText.includes("Create your account")',"registration form");
    const password="UiReview!"+require("node:crypto").randomBytes(16).toString("base64url")+"A9";
    for(const [index,value] of ["Synthetic UI Reviewer",isolatedUsername,isolatedUsername+"@example.com",password,password].entries())await fill("form input",value,index);
    await click("Create Account");report.synthetic_account=isolatedUsername;
  }
  await wait('document.body.innerText.includes("Your hiring workspace")',"authenticated home");
  passed("Recruiter authentication opens the guided hiring workspace");await shot("02-dashboard");
  const cookies=await call("Network.getCookies",{urls:[apiBase]});if(!cookies.cookies.some(c=>c.name==="sessionid"&&c.httpOnly))throw new Error("Session is not HttpOnly");
  await verifyNavigation();
  if(process.env.EVIDENCE_ONLY){await verifyEvidence();return;}
  if(process.env.AI_ONLY){await verifyAssistant();return;}
  const title="UI Review Backend "+Date.now();
  await go("/jobs");await click("Create job");await wait("!!document.querySelector('[role=\"dialog\"]')","job form");
  for(const [label,value] of [["Job title",title],["Company","Synthetic UI Lab"],["Location","Remote"],["Job description","Build Python and Django services using PostgreSQL."],["Required skills","Python, Django, PostgreSQL"],["Minimum experience","2"],["Education requirement","Bachelor of Computer Science"]])await fillLabel(label,value);
  await click("Suggest skills from description",'document.querySelector(\'[role="dialog"]\')');await wait('document.body.innerText.includes("Suggested skills:")',"in-context job suggestions");await click("Use these skills");
  await fillLabel("Required skills","Python, Django, PostgreSQL");
  await click("Create job",'document.querySelector(\'[role="dialog"]\')');await wait("!document.querySelector('[role=\"dialog\"]')","job created");
  const jobs=await api("/jobs/?search="+encodeURIComponent(title));jobId=jobs.data.results[0]?.id;if(!jobId)throw new Error("Job not saved");
  await wait('document.body.innerText.includes("Candidate matches")',"job workspace");
  await click("Job requirements");await click("Edit requirements");await expand("Additional job details and matching priorities",'document.querySelector(\'[role="dialog"]\')');
  await evaluate('document.querySelector(\'[role="dialog"] input[type="checkbox"]\').click()');
  for(const [index,value] of [60,20,20].entries())await fill('[role="dialog"] fieldset input',value,index);
  await click("Save requirements");await wait("!document.querySelector('[role=\"dialog\"]')","job priorities saved");
  const savedJob=await api("/jobs/"+jobId+"/");if(savedJob.data.scoring_weights.skills!==.6)throw new Error("Custom scoring priorities were lost");
  await click("Candidate matches");await shot("03-jobs");passed("Job form provides readable AI suggestions and retains editing, employment details and custom priorities");
  await go("/candidates?upload=1&job="+jobId);await wait("!!document.querySelector('[role=\"dialog\"] input[type=\"file\"]')","contextual resume upload");
  const files=[path.join(root,"evaluation/fixtures/sample-cv.docx"),path.join(root,"evaluation/fixtures/unreadable.pdf")];await uploadFiles(files);
  let candidate,blank;
  for(let i=0;i<120;i++){const response=await api("/candidates/?search=riley");candidate=response.data.results.find(c=>c.email==="riley@example.com"&&c.processing_status==="completed");if(candidate)break;await sleep(400);}
  if(!candidate)throw new Error("The background worker did not finish the synthetic resume");fixtureCandidateId=candidate.id;candidateIds.push(candidate.id);
  for(let i=0;i<80;i++){const response=await api("/candidates/?processing_status=failed");blank=response.data.results.find(c=>c.full_name==="unreadable");if(blank)break;await sleep(300);}
  if(!blank)throw new Error("Unreadable resume did not report failure");candidateIds.push(blank.id);
  await click("Upload resumes");await wait("!!document.querySelector('[role=\"dialog\"]')","duplicate upload");await uploadFiles(files);
  await wait('document.body.innerText.includes("0 files accepted; 2 need attention.")',"readable per-file validation errors");await shot("04-candidates");
  passed("Contextual bulk uploads, background extraction, unreadable-file failure and duplicate validation remain understandable");
  await go("/candidates/"+candidate.id+"?job="+jobId);await wait('document.body.innerText.includes("Check the resume details")',"candidate details");
  await expand("See where these details came from");await expand("Read original resume text");
  if(!await evaluate('document.body.innerText.includes("Postgres")'))throw new Error("Source resume evidence is missing");
  await click("Check candidate details");await fillLabel("Skills","Python, Django, PostgreSQL");await click("Confirm checked details");await wait("!document.querySelector('[role=\"dialog\"]')","profile checked");
  await wait('document.body.innerText.includes("Details checked by a recruiter")',"reviewed status");await shot("05-candidate-evidence");
  await click("Continue to job match");await click("Compare candidate");await wait('!!document.querySelector("[data-analysis-id]") && !Array.from(document.querySelectorAll("button")).some(b=>b.textContent.includes("Comparing this candidate")) && !document.body.innerText.includes("The job or candidate details have changed")',"fresh candidate comparison");
  for(let i=0;i<100;i++){const tasks=await api("/tasks/");if(!tasks.data.results.some(t=>["queued","running"].includes(t.status)))break;await sleep(300);}
  await wait('!Array.from(document.querySelectorAll("button")).find(b=>b.textContent==="Explain this match")?.disabled',"assistant ready");
  const updated=await api("/candidates/"+candidate.id+"/");if(!updated.data.profile_reviewed_at||!updated.data.skills.includes("PostgreSQL"))throw new Error("Profile correction not retained");
  await click("Explain this match");await wait('!Array.from(document.querySelectorAll("button")).some(b=>b.textContent.includes("Preparing explanation"))',"inline explanation");
  await click("Prepare interview questions");await wait('document.body.innerText.includes("Areas to explore")',"inline interview questions");
  await shot("18-candidate-match");passed("Candidate tabs preserve original evidence, profile correction, job-specific matching and contextual AI explanations/interviews");
  await click("Continue to review & decision");await click("Add candidate to this job");await wait('!!document.querySelector(\'select[aria-label="Next application stage"]\')',"application created");
  await select('select[aria-label="Next application stage"]',"review");await fill('textarea[aria-label="Human review note"]',"Checked the original resume and corrected the PostgreSQL skill.");await click("Save decision");await wait('Array.from(document.querySelectorAll("article span")).some(el=>el.textContent.trim()==="In review") && Array.from(document.querySelectorAll("button")).some(b=>b.textContent==="Save decision"&&!b.disabled)',"saved review stage");
  await select('select[aria-label="Next application stage"]',"shortlisted");await fill('textarea[aria-label="Human review note"]',"Confirmed skills and experience against this job before shortlisting.");await click("Save decision");await wait('Array.from(document.querySelectorAll("article span")).some(el=>el.textContent.trim()==="Shortlisted")',"saved shortlist stage");
  const apps=await api("/applications/?candidate="+candidate.id+"&job="+jobId);if(apps.data.count!==1||apps.data.results[0].decisions.length!==2)throw new Error("Job-scoped decision history was not saved");
  await expand("Decision history");await shot("06-human-review");passed("Human application stages and durable decision notes remain separate from advisory scores");
  await go("/jobs/"+jobId);await wait('document.body.innerText.includes("Riley Example")',"embedded matches");await shot("07-rankings");
  await go("/rankings?job="+jobId);await wait('document.body.innerText.includes("Riley Example")',"standalone rankings retained");
  await verifyAssistant();await verifyEvidence();
  await go("/automation");await wait('document.body.innerText.includes("Needs attention")',"processing activity");await expand("Advanced: refresh your whole candidate pool");
  if(!await evaluate('Array.from(document.querySelectorAll("button")).some(b=>b.textContent==="Try again")'))throw new Error("Task retry control is missing");await shot("09-automation-failure");
  await go("/candidates/"+blank.id);await wait('document.body.innerText.includes("Scanned/image-only")',"readable failure");await shot("10-unreadable-resume");
  if(!await evaluate('!!document.querySelector(\'input[aria-label="Replacement resume"]\')'))throw new Error("Resume replacement control is missing");
  passed("Processing retries, bulk refresh tools, private downloads and resume replacement remain available");
  await call("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:true});await go("/");await wait('document.body.innerText.includes("Your hiring workspace")',"mobile home");
  const mobile=await evaluate('Array.from(document.querySelectorAll(\'nav[aria-label="Mobile navigation"] a\')).map(a=>a.textContent)');if(mobile.length!==4)throw new Error("Mobile navigation lost a destination");
  if(await evaluate('document.documentElement.scrollWidth>innerWidth+1'))throw new Error("Mobile home has horizontal overflow");await shot("11-mobile-dashboard");passed("Mobile navigation stays compact with all advanced tools accessible");
  if(report.errors.length)throw new Error("Browser exceptions: "+report.errors.join(", "));
}
(async()=>{
  let failure;
  try{await main();if(report.errors.length)throw new Error("Browser exceptions: "+report.errors.join(", "));report.passed=true;}catch(error){failure=error;report.passed=false;report.failure=error.message;console.error(error.message);if(socket)try{await shot("failure");}catch{}}
  finally{
    if(socket){
      if(!focused&&!process.env.KEEP_E2E_DATA||failure)try{for(const id of candidateIds)await api("/candidates/"+id+"/","DELETE");if(jobId)await api("/jobs/"+jobId+"/","DELETE");report.fixture_cleanup=true;}catch{}
      try{await call("Browser.close");}catch{}socket.close();
    }
    report.finished_at=new Date().toISOString();report.ui_version="recruiter-workflow-v1";
    const file=process.env.EVIDENCE_ONLY?"verification-scoring-evaluation-browser.json":process.env.AI_ONLY?(process.env.LIVE_AI?"verification-ai-live-browser.json":"verification-ai-browser.json"):"verification-browser.json";
    fs.writeFileSync(path.join(root,"docs",file),JSON.stringify(report,null,2)+"\n");
  }
  if(failure)process.exit(1);
})().catch(error=>{console.error(error);process.exit(1);});
