# 요구사항 명세 (Requirements Specification)

## 프로젝트 개요

**목표**: GoogleCloudPlatform/zetasql-toolkit의 Java 구현을 Python으로 포팅하여 ZetaSQL 기반 리니지 추출 시연

**핵심 기능**:
1. 테이블 레벨 리니지 추출
2. 컬럼 레벨 리니지 추출

**참고 레포지토리**: `GoogleCloudPlatform/zetasql-toolkit`

## 포팅 대상 Java 파일

### 1. BigQuery Language Options
- **파일**: `zetasql-toolkit-bigquery/src/main/java/com/google/zetasql/toolkit/options/BigQueryLanguageOptions.java`
- **목적**: BigQuery SQL 방언에 맞는 LanguageOptions 설정
- **주요 기능**:
  - 80+ BigQuery 언어 기능 활성화 (JSON, GEOGRAPHY, NUMERIC, PIVOT, QUALIFY 등)
  - ProductMode.PRODUCT_EXTERNAL 설정
  - Statement kinds 설정 (SELECT, INSERT, UPDATE, MERGE, CREATE, DROP 등)

### 2. Column Lineage Extractor
- **파일**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ColumnLineageExtractor.java`
- **목적**: Resolved AST에서 컬럼 레벨 리니지 추출
- **지원 문법**:
  - SELECT
  - CREATE TABLE AS SELECT
  - CREATE VIEW AS SELECT
  - INSERT
  - UPDATE
  - MERGE

### 3. Parent Column Finder
- **파일**: `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/ParentColumnFinder.java`
- **목적**: 컬럼의 "terminal parent" (테이블에서 직접 읽는 컬럼) 찾기
- **알고리즘**: BFS를 통한 컬럼 부모 트리 순회

### 4. 기타 지원 클래스
- **ColumnEntity.java**: 컬럼 엔티티 (테이블명 + 컬럼명)
- **ColumnLineage.java**: 리니지 관계 (target 컬럼 + parent 컬럼 집합)

### 5. 예제 파일
- **파일**: `zetasql-toolkit-examples/src/main/java/com/google/zetasql/toolkit/examples/ExtractColumnLevelLineage.java`
- **목적**: 다양한 SQL 문에 대한 리니지 추출 시연

## 기능 요구사항

### FR-1: 카탈로그 생성
- **설명**: BigQuery 연결 없이 SimpleCatalog를 직접 생성
- **요구사항**:
  - BigQuery 스타일 테이블명 지원: `project.dataset.table`
  - 샘플 데이터셋 (orders, customers, products 등) 정의
  - CatalogBuilder와 TableBuilder를 활용한 fluent API

### FR-2: BigQuery Language Options
- **설명**: BigQuery SQL 방언 지원을 위한 언어 옵션 설정
- **요구사항**:
  - 80+ 언어 기능 활성화
  - 주요 기능: QUALIFY, PIVOT, UNPIVOT, JSON functions, GEOGRAPHY, NUMERIC types
  - 모든 주요 statement kinds 지원

### FR-3: 테이블 레벨 리니지 추출
- **설명**: SQL 문에서 소스 테이블과 타겟 테이블 추출
- **지원 SQL 문법**:
  - `SELECT` (읽기 전용 - 소스 테이블만)
  - `CREATE TABLE AS SELECT` (타겟: 생성되는 테이블, 소스: SELECT의 테이블들)
  - `CREATE VIEW AS SELECT` (타겟: 뷰, 소스: SELECT의 테이블들)
  - `INSERT INTO` (타겟: INSERT 대상 테이블, 소스: SELECT의 테이블들)
  - `UPDATE` (타겟: UPDATE 대상 테이블, 소스: WHERE/SET의 참조 테이블들)
  - `MERGE` (타겟: MERGE 대상 테이블, 소스: USING의 테이블들)
- **복잡한 쿼리 지원**:
  - 서브쿼리 (Subquery)
  - CTE (WITH 절)
  - 윈도우 함수 (Window Functions)
  - JOIN (모든 종류)

### FR-4: 컬럼 레벨 리니지 추출
- **설명**: 출력 컬럼과 입력 컬럼 간의 의존 관계 추출
- **지원 SQL 문법**: FR-3과 동일
- **추출 정보**:
  - Target column: 출력/대상 컬럼 (테이블명 + 컬럼명)
  - Parent columns: 해당 컬럼이 의존하는 소스 컬럼들 (테이블명 + 컬럼명)
- **복잡한 표현식 지원**:
  - 산술 연산: `price * quantity`
  - 함수 호출: `UPPER(name)`, `SUM(amount)`
  - CASE 표현식
  - 윈도우 함수: `ROW_NUMBER() OVER (PARTITION BY ...)`
  - 서브쿼리 내 컬럼 참조

### FR-5: 결과 포맷팅
- **설명**: 리니지 결과를 다양한 형식으로 출력
- **지원 형식**:
  - JSON: 프로그래밍 방식 처리 및 저장용
  - 텍스트: 사람이 읽기 쉬운 형식
- **출력 내용**:
  - 테이블 리니지: 소스 테이블 목록, 타겟 테이블
  - 컬럼 리니지: 각 타겟 컬럼별 부모 컬럼 목록

### FR-6: 시연 스크립트
- **설명**: 실행 가능한 예제 스크립트
- **요구사항**:
  - `demo_table_lineage.py`: 테이블 리니지 추출 시연
  - `demo_column_lineage.py`: 컬럼 리니지 추출 시연
  - 각 SQL 문법별 예제 포함
  - 결과를 JSON과 텍스트로 출력

## 비기능 요구사항

### NFR-1: 코드 가독성
- **설명**: 사용법 시연이 목적이므로 최대한 가독성 높은 코드 작성
- **요구사항**:
  - 명확한 클래스/함수명
  - 충분한 docstring과 타입 힌트
  - 간결한 함수 (하나의 함수는 하나의 책임)
  - 예제 코드에 주석 포함

### NFR-2: 테스트 커버리지
- **설명**: TDD 방식으로 개발
- **요구사항**:
  - 모든 지원 SQL 문법에 대한 단위 테스트
  - pytest 사용
  - 각 모듈별 독립적인 테스트 파일

### NFR-3: 프로젝트 구조
- **설명**: 명확한 폴더 구조
- **요구사항**:
  ```
  /
  ├── docs/                    # 프로젝트 문서
  ├── src/
  │   └── zetasql_demo/
  │       ├── catalog/         # 카탈로그 생성 모듈
  │       ├── options/         # BigQuery 옵션 모듈
  │       ├── lineage/         # 리니지 추출 모듈
  │       └── examples/        # 시연 스크립트
  ├── tests/                   # 단위 테스트
  ├── pytest.ini               # pytest 설정
  └── README.md                # 프로젝트 개요 및 사용법
  ```

### NFR-4: 의존성 관리
- **설명**: 최소한의 외부 의존성
- **요구사항**:
  - Python 3.10+
  - zetasql (이미 설치됨)
  - pytest (테스트용)
  - 표준 라이브러리 활용 (dataclasses, typing 등)

## 제약 사항

### C-1: BigQuery 연결 불가
- **설명**: BigQuery에 직접 연결할 수 없음
- **해결책**: SimpleCatalog를 사용하여 메모리 내 카탈로그 생성

### C-2: Python ZetaSQL API 제한
- **설명**: Java API와 완전히 동일하지 않을 수 있음
- **해결책**: Python API 문서와 예제를 참고하여 최선의 방법 사용

### C-3: 에러 처리 테스트 미포함
- **설명**: 에러 상황에 대한 테스트는 작성하지 않음
- **해결책**: 정상 경로(happy path)에 집중, 에러 발생 시 예외를 그대로 출력

## 성공 기준

### SC-1: 모든 테스트 통과
- 작성된 모든 pytest 테스트가 통과해야 함

### SC-2: 모든 SQL 문법 지원
- SELECT, CREATE TABLE AS SELECT, CREATE VIEW, INSERT, UPDATE, MERGE 모두 지원

### SC-3: 복잡한 쿼리 처리
- 서브쿼리, CTE, 윈도우 함수가 포함된 쿼리 처리 가능

### SC-4: 실행 가능한 예제
- `python src/zetasql_demo/examples/demo_table_lineage.py` 실행 시 명확한 결과 출력
- `python src/zetasql_demo/examples/demo_column_lineage.py` 실행 시 명확한 결과 출력

### SC-5: 문서화 완료
- README.md에 프로젝트 설명, 설치 방법, 실행 방법 포함
