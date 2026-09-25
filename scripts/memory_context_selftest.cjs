const fs=require('fs'), vm=require('vm'), assert=require('node:assert/strict');
const source=fs.readFileSync(require('path').join(__dirname,'../runtime_assets/app.js'),'utf8').replace(/init\(\)\.catch\([\s\S]*$/,'');
// Two fresh JS runtimes share synthetic persistent records; no phone data is read.
const persisted={memory:[{type:'tercih',text:'Sınama rengi turkuaz.'}],chats:[{sessionId:'old',role:'user',text:'Eski oturum gizlisi'},{sessionId:'new',role:'assistant',text:'Merhaba'}]};
const settings={};
function runtime(){const c=vm.createContext({window:{addEventListener(){}},localStorage:{getItem:k=>settings[k]??null},console});vm.runInContext(source,c);c.rows=persisted;vm.runInContext("all=async s=>rows[s];state.sessionId='new'",c);return c;}
(async()=>{
 let c=runtime(), text=await vm.runInContext("buildChatMessage('Rengim ne?')",c);
 assert(!text.includes('turkuaz'));assert(!text.includes('Eski oturum'));assert(text.includes('Merhaba'));
 settings.mehmet_memory_share_model='true';
 c=runtime();text=await vm.runInContext("buildChatMessage('Rengim ne?')",c);assert(text.includes('turkuaz'));
 settings.mehmet_memory_enabled='false';text=await vm.runInContext("buildChatMessage('Rengim ne?')",c);assert(!text.includes('turkuaz'));
 settings.mehmet_memory_enabled='true';persisted.memory=Array.from({length:100},()=>({type:'x'.repeat(500),text:'z'.repeat(9000)}));persisted.chats=Array.from({length:100},()=>({sessionId:'new',role:'user',text:'w'.repeat(5000)}));
 text=await vm.runInContext("buildChatMessage('q'.repeat(12000))",c);assert(text.length<32000);
 await assert.rejects(()=>vm.runInContext("buildChatMessage('q'.repeat(12001))",c));
 console.log('MEMORY_CONTEXT_TEST=PASS; OPT_IN=PASS; SESSION_ISOLATION=PASS; SIZE_BOUND=PASS; PHONE_INDEXEDDB=NOT_TESTED');
})().catch(e=>{console.error(e);process.exitCode=1});
