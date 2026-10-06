(function(){
"use strict";
var D=window.SITE_DATA||[];
var $=function(s,r){return (r||document).querySelector(s)};
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})};
var byId={};D.forEach(function(e){byId[e.id]=e});

/* ---------- 정적 데이터 (마스터 최종 종합안 · 강의 시간표 v2 기준) ---------- */
var WEEKS=[
 {n:1,t:'OT · 저널리즘 윤리 · 허위정보 대응',s:'①⑪⑭',d:'OT 2h, 콘텐츠 제작자의 윤리·법적 책임 14h, AI 콘텐츠 시대의 허위정보 대응 24h'},
 {n:2,t:'콘텐츠 도메인 세팅 1',s:'③',d:'뉴스+브랜드·제품·트렌드로 도메인 확장, 로봇저널리즘·AI 콘텐츠 생성 원리'},
 {n:3,t:'콘텐츠 도메인 세팅 2',s:'③',d:'GPTs·Gemini Gems·Claude Projects 기반 콘텐츠 자동화 실습'},
 {n:4,t:'콘텐츠 도메인 세팅 3',s:'③',d:'도메인별 톤앤매너 파인튜닝, AI 생성물 검수·품질개선 (③ 완료 120h)'},
 {n:5,t:'영상문법 · 프롬프트 · AI 삽화·영상',s:'④⑫',d:'영상문법 8h, 프롬프트 8h, AI 삽화·영상생성 16h, MBC 뉴스데스크 현장탐방 8h'},
 {n:6,t:'Premiere 편집 실무',s:'④',d:'컷편집·시퀀스·컬러·사운드 30h, AI 자동화통합 일부 10h'},
 {n:7,t:'After Effects 모션그래픽',s:'④',d:'로어써드·텍스트 애니메이션·2.5D 카메라 30h, Photoshop 일부 10h'},
 {n:8,t:'RAG 노코드 활용 · 프로젝트1 착수',s:'④⑦',d:'Photoshop·자동화통합 마무리 8h (④ 완료 120h), RAG 노코드 16h, 프로젝트1 착수 16h'},
 {n:9,t:'프로젝트1 완성·발표 · 현장실습',s:'⑦⑩',d:'이슈 리포트 영상 완성·발표 24h (⑦ 완료 56h), 제작현장지원실습 16h'},
 {n:10,t:'AI 팩트체킹 · RAG 원리',s:'⑤',d:'NotebookLM 등 노코드 활용법 핵심'},
 {n:11,t:'팩트체킹 심화',s:'⑤',d:'도메인별 케이스스터디, 검증 결과의 영상자막·카드뉴스 변환 (⑤ 완료 80h)'},
 {n:12,t:'데이터 탐사 · 프로젝트2 착수',s:'⑧',d:'AI 기반 데이터 탐사 핵심 활용법, 정보프로그램 기획'},
 {n:13,t:'프로젝트2 완성·발표 · 시각화 착수',s:'⑧⑥',d:'정보프로그램 완성·발표 32h (⑧ 완료 72h), 데이터시각화 착수 8h'},
 {n:14,t:'데이터 시각화 마무리',s:'⑥',d:'Matplotlib·Seaborn과 Flourish로 인포그래픽 완성 (⑥ 완료 48h)'},
 {n:15,t:'프로젝트3 시사 다큐멘터리 제작',s:'⑨',d:'데이터 시각화 활용 콘텐츠, 시사 다큐멘터리(10분 이내) 제작'},
 {n:16,t:'프로젝트3 완성 · 수료식',s:'⑨⑬',d:'다큐멘터리 완성 32h (⑨ 완료 72h), 수료식 8h, 프로젝트 1·2·3 종합 상영·발표'}
];
var CAPS=[
 {n:1,name:'이슈 리포트 영상',len:'3분 이내',lv:'1단계 · 속보성',wk:'8~9주차',ws:[8,9],sub:'⑦ RAG 모델 기반의 선거 보도 구성하기 (56h)',extra:'9주차 완성 직후 MBC 뉴스데스크 제작현장지원실습(16h)에서 실무 검증',desc:'자유주제(브랜드·트렌드·사회현상)를 데이터 근거로 3분 안에 정리하는 리포트 영상.'},
 {n:2,name:'정보프로그램',len:'제한 없음',lv:'2단계 · 심층 취재',wk:'12~13주차',ws:[12,13],sub:'⑧ AI 기반 데이터 탐사보도 및 기사 자동화 (72h)',extra:'13주차에 완성·발표, 데이터 시각화(⑥) 착수',desc:'데이터 탐사를 바탕으로 코너(VCR) 구성의 정보프로그램을 기획·제작.'},
 {n:3,name:'시사 다큐멘터리',len:'10분 이내',lv:'3단계 · 서사·최종',wk:'15~16주차',ws:[15,16],sub:'⑨ 데이터 시각화를 활용한 뉴스 콘텐츠 제작 (72h)',extra:'16주차 수료식에서 프로젝트 1·2·3 종합 상영·발표',desc:'데이터 시각화를 서사와 결합한 시사 다큐멘터리.'}
];
var CATS=[
 {k:'curriculum',r:'weeks',n:'주차별 강의자료',d:'1주차부터 16주차까지 강의안·워크시트·가이드'},
 {k:'capstone',r:'capstone',n:'캡스톤 프로젝트 3개',d:'이슈 리포트 · 정보프로그램 · 시사 다큐멘터리'},
 {k:'adobe',r:'adobe',n:'Adobe · Claude 연결',d:'Photoshop·Illustrator·Premiere·After Effects·C4D·Blender·Flow'},
 {k:'practice',r:'practice',n:'실습 자료',d:'코랩 노트북, 파이썬 예제, 데이터, API, 템플릿'},
 {k:'ops',r:'ops',n:'과정 운영',d:'마스터 최종 종합안, 시간표, 개선안, 홍보 자료'},
 {k:'lab',r:'lab',n:'실험실',d:'Blender 프리비즈, Claude Code로 만든 모션그래픽'}
];
var EXCL=[
 ['구글 제미니 API KEY.txt · 구글 KEY.png','API 키 파일입니다. 공개 사이트에 올리면 누구나 키를 쓸 수 있어 업로드하지 않았습니다.'],
 ['박스오피스 실습 코드의 KOBIS 인증키','boxoffice_kobis.py, boxoffice_july_monthly.py 두 파일에 인증키가 직접 들어 있었습니다. 사이트 사본에서는 자리표시자로 바꿨고, 원본 파일은 그대로입니다. 이미 공개된 적이 있다면 KOBIS에서 키를 재발급하세요.'],
 ['외부자료 · 사무직의 AI 리터러시 향상하기 (01~10)','외부에서 가져온 자료라 재배포 권한이 확인되지 않았습니다.'],
 ['챗GPT 상위 1% 업무 해킹 가이드 (PDF 19MB)','외부 저작물이라 제외했습니다.'],
 ['K정보프로그램의 해부학 · K콘텐츠의 진화 (PDF 17MB · 25MB)','외부 저작물이고 용량이 커서 제외했습니다.'],
 ['VideoHive 샘플 미리보기 영상, 모션 분석용 프레임 이미지','스톡 영상 미리보기라 라이선스상 재배포할 수 없습니다. 이 영상들을 분석해 쓴 모션패턴 분석 문서 3편은 실험실에 실려 있습니다.'],
 ['용량이 큰 중간 산출 영상 (car_history 계열 mp4)','최종본 car_history_vox.mp4만 올렸습니다. 깃허브 저장소 용량을 아끼기 위해서입니다.'],
 ['6~8주차 원본 PPTX · DOCX','파일 이름의 물결표(~) 때문에 전송되지 않아, 프로젝트에 저장된 텍스트로 복원한 문서 두 편으로 대체했습니다. 원본을 폴더에 두고 이름을 바꿔 주시면 교체할 수 있습니다.'],
 ['이전 파일명의 중복 파일 5개','week1_worksheet.pdf, 소비자보호원·스킨케어·연합뉴스·card_news 템플릿 xlsx 이전 이름본. 내용이 최신본(1주차·3주차 접두어)과 완전히 같아서 한 벌만 실었습니다.'],
 ['과정 홍보 포스터 원본 (course_promo_poster.pptx)','보강본(course_promo_poster_enhanced)으로 대체했습니다.']
];
var KORD=['강의안','슬라이드','실습 워크시트','가이드·자료','연결 가이드','과정 설계','웹 퀴즈','PDF 자료','자료','이전 초안','코랩 노트북','실습 코드','데이터·템플릿','이미지','영상'];
var GROUPS=[
 {n:'강의안·슬라이드',k:['강의안','슬라이드']},
 {n:'실습 워크시트',k:['실습 워크시트']},
 {n:'가이드·자료',k:['가이드·자료','연결 가이드','과정 설계','웹 퀴즈','PDF 자료','자료','이전 초안']},
 {n:'코랩·코드',k:['코랩 노트북','실습 코드']},
 {n:'데이터·템플릿',k:['데이터·템플릿']},
 {n:'이미지·영상',k:['이미지','영상']}
];
var CLASS={'①':'law','⑪':'law','⑭':'law','③':'ai','④':'vid','⑤':'fact','⑦':'fact','⑥':'data','⑧':'data','⑨':'data'};
var TL=[ /* [lane, start, len, cls, label, hours, week] */
 [2,1,1,'law','①⑪⑭',''],[2,2,3,'ai','③ 콘텐츠 도메인 세팅','120h'],[2,5,4,'vid','④ AI 협업 영상 제작','120h'],
 [2,10,2,'fact','⑤ AI 팩트체킹','80h'],[2,12,2,'data','⑧ 데이터 탐사','72h'],[2,15,2,'data','⑨ 시각화 콘텐츠','72h'],
 [3,8,2,'fact','⑦ RAG 보도','56h'],[3,13,2,'data','⑥ 데이터 시각화','48h'],
 [4,8,2,'proj','P1 이슈 리포트','3분'],[4,12,2,'proj','P2 정보프로그램',''],[4,15,2,'proj','P3 시사 다큐','10분'],
 [5,1,1,'field','OT','2h'],[5,5,1,'field','현장탐방','8h'],[5,9,1,'field','현장실습','16h'],[5,16,1,'field','수료식','']
];
var CAPLINK={'P1 이슈 리포트':1,'P2 정보프로그램':2,'P3 시사 다큐':3};

/* ---------- 유틸 ---------- */
function size(b){return b>=1048576?(b/1048576).toFixed(1)+'MB':Math.max(1,Math.round(b/1024))+'KB'}
function metaOf(e){var a=[];if(e.pg)a.push(e.pg+'쪽');a.push(size(e.s));return a.join(' · ')}
function isDeck(e){return !!e.th}
function row(e){
 return '<div class="row'+(e.p?' cp':'')+'"><span class="kd">'+esc(e.k)+'</span><div class="tt"><a href="#/doc/'+e.id+'">'+esc(e.t)+'</a>'+(e.d?'<small>'+esc(e.d)+'</small>':'')+'</div><span class="sz">'+metaOf(e)+'</span><a class="dl" href="'+e.f+'" download>내려받기</a></div>';
}
function deck(e){
 return '<a class="deck" href="#/doc/'+e.id+'"><img loading="lazy" src="'+e.th+'" alt="'+esc(e.t)+' 첫 장"><div class="t">'+esc(e.t)+'</div><div class="m">'+metaOf(e)+'</div></a>';
}
function pic(e){
 return '<a class="deck" href="#/doc/'+e.id+'"><img loading="lazy" src="'+e.f+'" alt="'+esc(e.t)+'"><div class="t">'+esc(e.t)+'</div><div class="m">'+size(e.s)+'</div></a>';
}
function grouped(list){
 var out='';
 GROUPS.forEach(function(g){
  var items=list.filter(function(e){return g.k.indexOf(e.k)>=0});
  if(!items.length)return;
  items.sort(function(a,b){return KORD.indexOf(a.k)-KORD.indexOf(b.k)||a.t.localeCompare(b.t,'ko',{numeric:true})});
  var dk=items.filter(isDeck),pics=items.filter(function(e){return e.vt==='img'&&!isDeck(e)&&e.s<2500000}),rest=items.filter(function(e){return !isDeck(e)&&!(e.vt==='img'&&e.s<2500000)});
  out+='<section class="grp"><h3>'+g.n+'<em>'+items.length+'개</em></h3>';
  if(dk.length)out+='<div class="decks">'+dk.map(deck).join('')+'</div>';
  if(pics.length)out+='<div class="decks" style="margin-top:'+(dk.length?18:0)+'px">'+pics.map(pic).join('')+'</div>';
  if(rest.length)out+='<div class="rows" style="margin-top:'+((dk.length||pics.length)?18:0)+'px">'+rest.map(row).join('')+'</div>';
  out+='</section>';
 });
 return out;
}
function setTitle(t){document.title=t?t+' | 데이터 저널리스트 커리큘럼':'데이터 저널리스트 커리큘럼'}
function weekEntries(n){return D.filter(function(e){return e.w.indexOf(n)>=0})}
function capEntries(c){
 return D.filter(function(e){return e.p===c.n||(e.k==='강의안'&&e.w.some(function(w){return c.ws.indexOf(w)>=0}))});
}

/* ---------- 페이지 ---------- */
function timeline(){
 var h='<div class="tlwrap"><div class="tlscroll"><div class="tl" id="tl" role="group" aria-label="16주 커리큘럼 타임라인">';
 h+='<div class="gridlines">'+new Array(17).join('<i></i>')+'</div>';
 h+='<div class="tl-grid"><div class="lab" style="grid-row:1">주차</div>';
 WEEKS.forEach(function(w){h+='<a class="wk" data-n="'+w.n+'" style="grid-row:1;grid-column:'+(w.n+1)+'" href="#/week/'+w.n+'" aria-label="'+w.n+'주차 '+esc(w.t)+'">'+(w.n<10?'0'+w.n:w.n)+'</a>'});
 h+='<div class="lab" style="grid-row:2">교과목</div><div class="lab" style="grid-row:4">캡스톤</div><div class="lab" style="grid-row:5">MBC 현장</div>';
 TL.forEach(function(t){
  var href=CAPLINK[t[4]]?'#/capstone/'+CAPLINK[t[4]]:'#/week/'+t[1];
  var label=t[4]+(t[5]?'<small>'+t[5]+'</small>':'');
  h+='<a class="clip '+t[3]+'" style="grid-row:'+t[0]+';grid-column:'+(t[1]+1)+' / span '+t[2]+'" href="'+href+'" title="'+esc(t[4]+(t[5]?' · '+t[5]:''))+'">'+label+'</a>';
 });
 h+='</div><div class="playhead sweep" id="ph"><b id="phb"></b></div></div></div>';
 h+='<div class="hint">좌우로 밀어서 전체 16주를 볼 수 있습니다.</div>';
 h+='<div class="legend"><span style="--c:var(--c-law)">윤리·법</span><span style="--c:var(--c-ai)">AI 콘텐츠 세팅</span><span style="--c:var(--c-vid)">영상 제작</span><span style="--c:var(--c-fact)">팩트체킹·RAG</span><span style="--c:var(--c-data)">데이터 탐사·시각화</span><span style="--c:var(--coral)">캡스톤 프로젝트</span></div></div>';
 return h;
}
function wireTimeline(){
 var tl=$('#tl');if(!tl)return;var ph=$('#ph'),pb=$('#phb');
 function at(n){
  ph.classList.remove('sweep');ph.style.opacity=1;
  ph.style.left='calc(96px + (100% - 106px) * '+((n-.5)/16)+')';
  ph.classList.toggle('flip',n>12);
  pb.textContent=n+'주차 · 누적 '+(n*40)+'h / 640h';
  [].forEach.call(tl.querySelectorAll('.wk'),function(a){a.classList.toggle('on',+a.dataset.n===n)});
 }
 [].forEach.call(tl.querySelectorAll('.wk'),function(a){
  a.addEventListener('mouseenter',function(){at(+a.dataset.n)});
  a.addEventListener('focus',function(){at(+a.dataset.n)});
 });
 ph.addEventListener('animationend',function(){ph.classList.remove('sweep');ph.style.opacity=0});
 tl.addEventListener('mouseleave',function(){ph.style.opacity=0;[].forEach.call(tl.querySelectorAll('.wk.on'),function(a){a.classList.remove('on')})});
 pb.textContent='1주차 · 누적 40h / 640h';
 var m=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
 if(m){ph.classList.remove('sweep');ph.style.opacity=0}
}
function home(){
 setTitle('');
 var n=D.length;
 var h='<section class="hero"><h1 class="disp">데이터 저널리스트<br>커리큘럼</h1>'+
 '<p class="lead">MBC 미디어캠퍼스 AI 기반 데이터 저널리스트 양성과정의 16주 강의자료입니다. 데이터로 검증된 사실을 담은 영상을 만드는 과정으로, 주차별 강의안부터 캡스톤 3개, Adobe와 Claude 연결 가이드까지 한곳에 모았습니다.</p>'+
 '<div class="facts"><span><b>640시간</b> 16주 · 주 40시간</span><span><b>3개</b> 캡스톤 프로젝트</span><span><b>'+n+'개</b> 자료</span></div></section>'+
 timeline()+
 '<div class="wkgrid">'+WEEKS.map(function(w){return '<a href="#/week/'+w.n+'"><b>'+(w.n<10?'0'+w.n:w.n)+'</b><span>'+esc(w.t)+'</span></a>'}).join('')+'</div>'+
 '<section class="sec"><h2>캡스톤 프로젝트</h2><p class="lead">난이도가 1단계에서 3단계로 오르는 프로젝트 3개입니다.</p><div class="capl">'+
 CAPS.map(function(c){return '<a href="#/capstone/'+c.n+'"><span class="n">'+c.n+'</span><span class="tt">'+esc(c.name)+'</span><span class="rt">'+esc(c.len)+' · '+esc(c.wk)+'</span><span class="ds">'+esc(c.desc)+'</span></a>'}).join('')+'</div></section>'+
 '<section class="sec"><h2>자료 모음</h2><div class="cats">'+
 CATS.map(function(c){var cnt=c.k==='capstone'?D.filter(function(e){return e.p}).length:D.filter(function(e){return e.c===c.k}).length;
  return '<a href="#/'+c.r+'"><b>'+esc(c.n)+'<em>'+cnt+'</em></b><span>'+esc(c.d)+'</span></a>'}).join('')+
 '<a href="#/all"><b>전체 자료 검색<em>'+n+'</em></b><span>제목·종류로 찾기</span></a></div></section>'+
 '<section class="sec"><h2>이 사이트의 기준</h2><p class="lead">모든 자료는 최종 확정안인 <a href="#/doc/op121" style="text-decoration:underline;text-underline-offset:3px">마스터 최종 종합안</a>을 기준으로 정리했습니다. 올리지 못한 자료와 그 이유는 <a href="#/excluded" style="text-decoration:underline;text-underline-offset:3px">미수록 목록</a>에 있습니다.</p></section>';
 return h;
}
function weeksIndex(){
 setTitle('주차별');
 return '<div class="crumb"><a href="#/">홈</a></div><div class="whead"><h1 class="disp" style="font-size:clamp(2rem,5vw,3.4rem)">주차별 강의자료</h1></div>'+
 '<div class="rows" style="margin-top:22px">'+WEEKS.map(function(w){var c=weekEntries(w.n).length;
  return '<div class="row" style="grid-template-columns:70px 1fr auto"><span class="kd" style="border:0;font:400 1.5rem/1 var(--f-disp);color:var(--coral);padding:0">'+(w.n<10?'0'+w.n:w.n)+'</span><div class="tt"><a href="#/week/'+w.n+'">'+esc(w.t)+'</a><small>'+esc(w.d)+'</small></div><span class="sz">'+c+'개</span></div>'}).join('')+'</div>';
}
function weekPage(n){
 var w=WEEKS[n-1];if(!w)return notFound();
 setTitle(n+'주차 '+w.t);
 var list=weekEntries(n);
 var h='<div class="crumb"><a href="#/">홈</a> / <a href="#/weeks">주차별</a></div><div class="whead"><span class="big">'+(n<10?'0'+n:n)+'</span><div><h1>'+esc(w.t)+'</h1><div class="sub">교과목 '+esc(w.s)+' · '+esc(w.d)+'</div></div></div>';
 if(n>=6&&n<=8)h+='<p class="note">6~8주차는 별도 강의안 없이 통합 실습 가이드로 진행합니다. 아래 통합 자료는 세 주차에 모두 표시됩니다.</p>';
 var cap=CAPS.filter(function(c){return c.ws.indexOf(n)>=0})[0];
 if(cap)h+='<p class="note" style="border-color:var(--coral)">이 주차는 <a href="#/capstone/'+cap.n+'" style="text-decoration:underline;text-underline-offset:3px">프로젝트'+cap.n+' '+esc(cap.name)+'</a> 기간입니다.</p>';
 h+=list.length?grouped(list):'<p class="lead" style="margin-top:28px">이 주차에 올라온 자료가 없습니다.</p>';
 h+='<div class="pn">'+(n>1?'<a href="#/week/'+(n-1)+'">이전 주차 '+(n-1)+'</a>':'<span></span>')+(n<16?'<a href="#/week/'+(n+1)+'">다음 주차 '+(n+1)+'</a>':'<span></span>')+'</div>';
 return h;
}
function capIndex(){
 setTitle('캡스톤 프로젝트');
 return '<div class="crumb"><a href="#/">홈</a></div><div class="whead"><h1 class="disp" style="font-size:clamp(2rem,5vw,3.4rem)">캡스톤 프로젝트 3개</h1></div><p class="lead" style="margin-top:14px">프로젝트 1에서 3으로 갈수록 난이도가 올라갑니다. 각 프로젝트는 연계 교과목의 수업과 함께 진행됩니다.</p><div class="capl" style="margin-top:22px">'+
 CAPS.map(function(c){return '<a href="#/capstone/'+c.n+'"><span class="n">'+c.n+'</span><span class="tt">'+esc(c.name)+'</span><span class="rt">'+esc(c.len)+' · '+esc(c.wk)+'</span><span class="ds">'+esc(c.desc)+' 연계 과목: '+esc(c.sub)+'</span></a>'}).join('')+'</div>';
}
function capPage(n){
 var c=CAPS[n-1];if(!c)return notFound();
 setTitle('프로젝트'+n+' '+c.name);
 var h='<div class="crumb"><a href="#/">홈</a> / <a href="#/capstone">캡스톤</a></div><div class="whead"><span class="big">P'+n+'</span><div><h1>'+esc(c.name)+'</h1><div class="sub">'+esc(c.desc)+'</div></div></div>'+
 '<dl class="cinfo"><div><dt>분량</dt><dd>'+esc(c.len)+'</dd></div><div><dt>난이도</dt><dd>'+esc(c.lv)+'</dd></div><div><dt>배치</dt><dd>'+esc(c.wk)+'</dd></div><div><dt>연계 과목</dt><dd>'+esc(c.sub)+'</dd></div><div><dt>연계 일정</dt><dd>'+esc(c.extra)+'</dd></div></dl>';
 h+=grouped(capEntries(c));
 h+='<div class="pn">'+(n>1?'<a href="#/capstone/'+(n-1)+'">프로젝트 '+(n-1)+'</a>':'<span></span>')+(n<3?'<a href="#/capstone/'+(n+1)+'">프로젝트 '+(n+1)+'</a>':'<span></span>')+'</div>';
 return h;
}
function adobePage(){
 setTitle('Adobe · Claude 연결');
 var rows=[
  ['Photoshop','Claude 설정 파일에 서버 한 줄(npx) 등록','앱 쪽 패널이 필요 없고, 포토샵만 켜 두면 됩니다'],
  ['Illustrator','Claude 설정 파일에 서버 한 줄(npx) 등록','문서를 열어 두고 작업하며, 항상 활성 문서에 적용됩니다'],
  ['Premiere Pro','Node.js 서버 + 확장 패널(MCP Bridge, 포트 8097)','패널을 열어 두어야 하고, 한글 Windows에서는 설정 파일 2곳을 고쳐야 합니다'],
  ['After Effects','Node.js 서버 + 브리지 스크립트 패널(mcp-bridge-auto.jsx)','패널을 열어 두고, 스크립트의 파일 쓰기를 허용해야 합니다'],
  ['Cinema 4D','Python 서버 + C4D 소켓 서버 플러그인(포트 5555)','C4D를 켤 때마다 Start Server를 눌러야 합니다'],
  ['Blender','Blender 공식 MCP 애드온(localhost 9876) + Claude 커넥터','애드온 서버가 꺼져 있으면 연결되지 않습니다'],
  ['Google Flow','Claude in Chrome으로 로그인된 화면 조작','별도 API가 없고, 크레딧 승인은 사용자가 확인합니다']
 ];
 var h='<div class="crumb"><a href="#/">홈</a></div><div class="whead"><h1 class="disp" style="font-size:clamp(2rem,5vw,3.4rem)">Adobe · Claude 연결</h1></div>'+
 '<p class="lead" style="margin-top:14px">Claude Desktop에 MCP 서버를 연결하면 말로 지시해 Adobe 프로그램과 C4D, Blender를 조작할 수 있습니다. 직접 설치하며 막혔던 지점과 해결법까지 정리한 가이드입니다.</p>'+
 '<p class="note">공통 조건: Claude Desktop 앱이 필요합니다(웹·모바일 불가). 설정 파일(claude_desktop_config.json)을 고친 뒤에는 창을 닫는 것으로는 부족하고, 트레이 아이콘에서 완전히 종료한 뒤 다시 실행해야 합니다. JSON은 항목 사이 쉼표 하나만 빠져도 전체가 읽히지 않습니다.</p>'+
 '<section class="grp"><h3>프로그램별 연결 방식</h3><div class="tw"><table class="t"><thead><tr><th>프로그램</th><th>연결 방식</th><th>알아둘 점</th></tr></thead><tbody>'+
 rows.map(function(r){return '<tr><td><b>'+r[0]+'</b></td><td>'+r[1]+'</td><td>'+r[2]+'</td></tr>'}).join('')+'</tbody></table></div></section>';
 var order=['Photoshop','Illustrator','Premiere Pro','After Effects','Cinema 4D','Blender','Google Flow','워크플로'];
 var list=D.filter(function(e){return e.c==='adobe'});
 order.forEach(function(t){
  var it=list.filter(function(e){return e.g===t});if(!it.length)return;
  var name=t==='워크플로'?'제작 워크플로':t;
  h+='<section class="grp"><h3>'+esc(name)+'<em>'+it.length+'개</em></h3>';
  var pics=it.filter(function(e){return e.vt==='img'}),rest=it.filter(function(e){return e.vt!=='img'});
  if(rest.length)h+='<div class="rows">'+rest.map(row).join('')+'</div>';
  if(pics.length)h+='<div class="decks" style="margin-top:18px">'+pics.map(pic).join('')+'</div>';
  h+='</section>';
 });
 return h;
}
function catPage(key,title,lead){
 setTitle(title);
 var list=D.filter(function(e){return e.c===key});
 return '<div class="crumb"><a href="#/">홈</a></div><div class="whead"><h1 class="disp" style="font-size:clamp(2rem,5vw,3.4rem)">'+esc(title)+'</h1></div><p class="lead" style="margin-top:14px">'+esc(lead)+'</p>'+grouped(list);
}
function allPage(q,c){
 setTitle('전체 자료');
 var h='<div class="crumb"><a href="#/">홈</a></div><div class="whead"><h1 class="disp" style="font-size:clamp(2rem,5vw,3.4rem)">전체 자료</h1></div>'+
 '<input class="bigsearch" id="aq" type="search" placeholder="제목, 종류, 주차로 검색 (예: 5주차, 코랩, 팩트체크)" value="'+esc(q)+'" aria-label="전체 자료 검색" autocomplete="off">'+
 '<div class="filters" id="chips"></div><div class="count" id="cnt" aria-live="polite"></div><div class="rows" id="res"></div>';
 return h;
}
function wireAll(q,c){
 var inp=$('#aq'),chips=$('#chips'),res=$('#res'),cnt=$('#cnt'),cur=c||'';
 var opts=[['','전체']].concat(CATS.filter(function(x){return x.k!=='capstone'}).map(function(x){return [x.k,x.n]})).concat([['cap','캡스톤']]);
 function hay(e){return (e.t+' '+e.k+' '+e.d+' '+e.g+' '+(e.w.length?e.w.map(function(w){return w+'주차'}).join(' '):'')+' '+(e.p?'프로젝트'+e.p+' 캡스톤':'')+' '+e.x).toLowerCase()}
 function draw(){
  chips.innerHTML=opts.map(function(o){return '<button class="chip" data-k="'+o[0]+'" aria-pressed="'+(cur===o[0])+'">'+o[1]+'</button>'}).join('');
  var qq=inp.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  var l=D.filter(function(e){
   if(cur==='cap'&&!e.p)return false;
   if(cur&&cur!=='cap'&&e.c!==cur)return false;
   var h=hay(e);return qq.every(function(t){return h.indexOf(t)>=0});
  });
  cnt.textContent=l.length+'개 자료';
  res.innerHTML=l.length?l.map(row).join(''):'<p class="lead" style="padding:24px 4px">검색 결과가 없습니다. 다른 단어로 찾거나 종류 필터를 &#39;전체&#39;로 바꿔 보세요.</p>';
 }
 chips.addEventListener('click',function(ev){var b=ev.target.closest('.chip');if(!b)return;cur=b.dataset.k;draw()});
 inp.addEventListener('input',draw);draw();
 $('#sq').value=q||'';
}
function docPage(id){
 var e=byId[id];if(!e)return notFound();
 setTitle(e.t);
 var back=e.p?'#/capstone/'+e.p:(e.w.length?'#/week/'+e.w[0]:'#/'+({adobe:'adobe',practice:'practice',ops:'ops',lab:'lab',curriculum:'weeks'}[e.c]||''));
 var h='<div class="crumb"><a href="#/">홈</a> / <a href="'+back+'">목록으로</a></div><div class="vbar"><h1>'+esc(e.t)+'</h1>'+
 '<a class="btn pri" href="'+e.f+'" download>원본 내려받기</a>'+(e.v?'<a class="btn" href="'+e.v+'" target="_blank" rel="noopener">새 탭에서 열기</a>':'')+(e.v&&e.vt!=='img'&&e.vt!=='video'?'<button class="btn" id="fs" type="button">전체화면</button>':'')+'</div>';
 if(e.r)h+='<p class="vwarn">이 파일의 API 인증키는 자리표시자로 바꿔 두었습니다. 직접 발급받은 키를 입력해 사용하세요.</p>';
 if(e.vt==='pdf')h+='<iframe class="frame" id="fr" title="'+esc(e.t)+'" src="'+e.v+'#view=FitH"></iframe><p class="vnote">'+metaOf(e)+' · 화면에 문서가 보이지 않으면(일부 휴대폰) 위의 [새 탭에서 열기]를 누르세요.</p>';
 else if(e.vt==='html')h+='<iframe class="frame" id="fr" title="'+esc(e.t)+'" src="'+e.v+'"></iframe><p class="vnote">'+metaOf(e)+'</p>';
 else if(e.vt==='img')h+='<img class="vmedia" style="background:none" src="'+e.v+'" alt="'+esc(e.t)+'">';
 else if(e.vt==='video')h+='<video class="vmedia" controls preload="metadata" src="'+e.v+'"></video><p class="vnote">'+metaOf(e)+'</p>';
 else h+='<div class="nofile"><p>미리보기를 지원하지 않는 파일입니다 (.'+esc(e.x)+', '+size(e.s)+').</p><p>[원본 내려받기]로 받아 해당 프로그램에서 열어 주세요.</p></div>';
 if(e.d)h+='<p class="vnote">'+esc(e.d)+'</p>';
 return h;
}
function excludedPage(){
 setTitle('미수록 목록');
 return '<div class="crumb"><a href="#/">홈</a></div><div class="whead"><h1 class="disp" style="font-size:clamp(2rem,5vw,3.4rem)">미수록 목록</h1></div><p class="lead" style="margin-top:14px">이 사이트는 공개 주소로 배포됩니다. 그래서 키·외부 저작물·용량 문제가 있는 자료는 싣지 않았고, 아래에 이유를 적었습니다.</p><div class="ex" style="margin-top:22px">'+
 EXCL.map(function(x){return '<div><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div>';
}
function notFound(){setTitle('찾을 수 없음');return '<div class="crumb"><a href="#/">홈</a></div><p class="lead" style="margin-top:40px">요청한 페이지를 찾을 수 없습니다. <a href="#/" style="text-decoration:underline">홈으로 돌아가기</a></p>'}

/* ---------- 라우터 ---------- */
var NAV=[['','홈'],['weeks','주차별'],['capstone','캡스톤'],['adobe','Adobe · Claude'],['practice','실습 자료'],['ops','과정 운영'],['lab','실험실'],['all','전체 자료'],['excluded','미수록']];
function route(){
 var raw=(location.hash||'#/').replace(/^#\/?/,''),qs='',p=raw.split('?');raw=p[0];qs=p[1]||'';
 var seg=raw.split('/'),page=seg[0],arg=seg[1];
 var params={};qs.split('&').forEach(function(kv){if(!kv)return;var a=kv.split('=');params[a[0]]=decodeURIComponent((a[1]||'').replace(/\+/g,' '))});
 var html,after;
 switch(page){
  case '':html=home();after=wireTimeline;break;
  case 'weeks':html=weeksIndex();break;
  case 'week':html=weekPage(+arg);break;
  case 'capstone':html=arg?capPage(+arg):capIndex();break;
  case 'adobe':html=adobePage();break;
  case 'practice':html=catPage('practice','실습 자료','코랩 노트북, 파이썬 예제, 수집·분석용 데이터, API 정보, 템플릿입니다. 주차가 정해진 자료는 해당 주차 페이지에도 있습니다.');break;
  case 'ops':html=catPage('ops','과정 운영','마스터 최종 종합안과 시간표, 세부 내용 개선안, 7단계 파이프라인 개정안, 홍보 자료입니다. 충돌하면 마스터 최종 종합안이 기준입니다.');break;
  case 'lab':html=catPage('lab','실험실','Blender 프리비즈와 Claude Code로 만든 모션그래픽 등, 수업 밖에서 실험한 결과물입니다.');break;
  case 'all':html=allPage(params.q||'',params.c||'');after=function(){wireAll(params.q||'',params.c||'')};break;
  case 'doc':html=docPage(arg);after=function(){var b=$('#fs');if(b)b.addEventListener('click',function(){var f=$('#fr');if(f&&f.requestFullscreen)f.requestFullscreen()})};break;
  case 'excluded':html=excludedPage();break;
  default:html=notFound();
 }
 var app=$('#app');app.innerHTML=html;
 var cur=page==='week'?'weeks':page==='doc'?'-':page;
 [].forEach.call(document.querySelectorAll('#nav a'),function(a){if(a.dataset.r===cur)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
 if(after)after();
 window.scrollTo(0,0);
 if(page!=='home'&&page!==''){app.focus({preventScroll:true})}
}
$('#nav').innerHTML=NAV.map(function(n){return '<a data-r="'+n[0]+'" href="#/'+n[0]+'">'+n[1]+'</a>'}).join('');
$('#foot').innerHTML='총 '+D.length+'개 자료 · 최종 확정안(마스터 문서) 기준 · MBC 미디어캠퍼스 AI 기반 데이터 저널리스트 양성과정 · 2026년 10월 정리';
$('#sform').addEventListener('submit',function(ev){ev.preventDefault();var v=$('#sq').value.trim();location.hash='#/all'+(v?'?q='+encodeURIComponent(v):'')});
window.addEventListener('hashchange',route);
route();
})();
