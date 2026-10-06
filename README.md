# 데이터 저널리스트 커리큘럼

MBC 미디어캠퍼스 AI 기반 데이터 저널리스트 양성과정 16주 강의자료 사이트입니다. 빌드 과정이 없는 정적 사이트입니다.

## GitHub Pages 배포
1. GitHub에서 새 저장소를 만듭니다 (예: journalist-curriculum).
2. 이 폴더의 모든 파일(index.html, data.js, assets, files, view, thumb, .nojekyll)을 저장소 최상위에 올립니다.
3. Settings > Pages > Branch를 main, 폴더를 / (root)로 지정하고 저장합니다.
4. 1~2분 뒤 https://<계정>.github.io/<저장소>/ 에서 열립니다.

로컬에서 볼 때는 폴더에서 `python -m http.server`를 실행해 열기를 권합니다. index.html을 바로 열면 PDF 미리보기가 안 보일 수 있습니다.

## 자료 추가하기
1. 파일을 files/ 에 넣습니다. PDF·이미지·영상은 그대로 미리보기가 됩니다. docx·pptx는 PDF로 변환해 view/ 에 같은 이름으로 넣으세요.
2. data.js 에 항목을 추가합니다. 필드: id(고유 이름), t(제목), c(curriculum/adobe/practice/ops/lab), w(주차 배열), p(캡스톤 번호 또는 null), k(종류), d(설명), x(확장자), v(미리보기 경로), vt(pdf/html/img/video), f(원본 경로), s(바이트 크기).

## 주의
- API 키·개인정보가 든 파일은 올리지 마세요. 저장소가 공개되면 누구나 내려받을 수 있습니다.
- 사이트 사본의 KOBIS 코드(boxoffice_*.py)는 인증키를 자리표시자로 바꿔 두었습니다.
- 올리지 않은 자료와 이유는 사이트의 미수록 페이지에 있습니다.
