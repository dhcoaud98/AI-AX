# AI-AX 

**git 로컬 환경 연결하기 ​​** 

1. GIT 로컬 환경 다운로드

2. GIT 로컬 저장소 만들기

   1. ```bash
      mkdir ~/{디렉토리명} && cd ~/test
      ```

   2. 생성된 디렉토리 초기화(init)하여 Git 로컬 저장소로 생성

      ```bash
      git init .
      ```

      :small_red_triangle_down: 성공적으로 로컬 저장소가 생성되면 Git bash 터미널 명령어 라인 앞에 현재 Git 기본 브랜치 이름을 나타내는 "(master)"가 붙는다. 

   3. ```bash
      # 숨겨진 디렉토리 조회 하면 디렉토리 내의 모든 이력을 객체(스냅샷과 비슷)로 저장하는 '.git' 디텍토리가 생성 됨을 알 수 있다.
      
      ls -al
      ```

   4. 만약 로컬 저장소를 일반 폴더로 변경하고 싶으면 다음과 같이 입력하면 된다.

      ```bash
      rm -rf .git/
      ```

3. git에 생성된 저장소의 url을 복사한다.

4. ```bash
   git remote add origin {git 저장소 url}
   ```

5. ```bash
   # 연결된 원격저장소 정보 확인하기
   
   git remote -v
   ```

6. ```bash
   # 연결된 저장소 삭제
   
   git remote remove origin
   ```

**로컬 :arrow_forward: 원격 올리기** (로컬 환경에 git 설정 + 저장소 연결 완료 후)

1. ```bash
   git add . 
   or
   git add {파일명}
   ```

2. ```bash
   # 로그와 상태 확인
   
   git log
   git status
   ```

3. ```bash
   # 로컬 저장소에 변경사항 커밋하기
   
   git commit -m "first-commit"
   ```

4. ```bash
   # 원격 저장소에 푸쉬하기
   
   git push 
   ```



:warning: ```git push origin master``` 이후 계속해서 username, password(토큰) 입력하는 경우

1. ```bash
   git config --global user.name {깃헙 id}
   ```

2. ```bash
   git config --gloval user.email {깃헙이메일주소}
   ```

3. ```bash
   git config credential.helper store --global
   ```

4. 한번 더 username, password(토큰) 입력해서 push

5. ```bash
   git config credential.helper store --global
   ```

   
