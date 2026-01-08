# ZetaSQL Lineage Demo - Project Overview

## 프로젝트 목표

GoogleCloudPlatform/zetasql-toolkit의 Java 구현을 Python으로 포팅하여 ZetaSQL 기반 리니지 추출 기능을 시연하는 프로젝트입니다.

## 핵심 기능

### 1. 테이블 레벨 리니지 추출
- SQL 쿼리에서 소스 테이블과 타겟 테이블의 관계를 추출
- 지원 SQL 문법: SELECT, CREATE TABLE AS SELECT, CREATE VIEW, INSERT, UPDATE, MERGE

### 2. 컬럼 레벨 리니지 추출
- 타겟 컬럼이 어떤 소스 컬럼들로부터 파생되었는지 추적
- 복잡한 쿼리(서브쿼리, CTE, 윈도우 함수 등) 지원
- Java zetasql-toolkit의 ColumnLineageExtractor, ParentColumnFinder 로직 포팅

## 참조 구현

### Java zetasql-toolkit
- 위치: `.reference/zetasql-toolkit/`
- 핵심 모듈:
  - `zetasql-toolkit-bigquery/src/main/java/com/google/zetasql/toolkit/options/BigQueryLanguageOptions.java`
  - `zetasql-toolkit-core/src/main/java/com/google/zetasql/toolkit/tools/lineage/`
  - `zetasql-toolkit-examples/src/main/java/com/google/zetasql/toolkit/examples/ExtractColumnLevelLineage.java`

## Python ZetaSQL API 활용

### 주요 API
- `zetasql.api.Analyzer`: SQL 문 분석
- `zetasql.api.ResolvedNodeVisitor`: AST 순회를 위한 Visitor 패턴
- `zetasql.api.CatalogBuilder`, `TableBuilder`: 카탈로그 생성
- `zetasql.types.LanguageOptions`: 언어 기능 설정
- `zetasql.types.ResolvedStatement`: 분석된 SQL AST

## 개발 방법론

### TDD (Test-Driven Development)
1. **Red**: 실패하는 테스트 먼저 작성
2. **Green**: 최소한의 코드로 테스트 통과
3. **Refactor**: 코드 품질 개선

### 단계별 진행
각 기능 모듈마다:
1. 테스트 케이스 작성 (전체 지원 SQL 문법 포함)
2. 점진적 구현 (문법별로 하나씩 해결)
3. 리팩토링 및 문서화

## 프로젝트 구조

```
zetasql-py-demo/
├── src/
│   └── zetasql_demo/
│       ├── catalog/          # 테스트용 카탈로그 생성
│       ├── options/          # BigQuery LanguageOptions 포팅
│       ├── lineage/          # 리니지 추출 핵심 로직
│       │   ├── models.py     # 데이터 모델 (dataclass)
│       │   ├── table_lineage.py
│       │   ├── column_lineage.py
│       │   └── formatters.py # JSON/텍스트 출력
│       └── examples/         # 실행 가능한 데모 스크립트
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── test_catalog.py
│   ├── test_bigquery_options.py
│   ├── test_table_lineage.py
│   ├── test_column_lineage.py
│   └── test_formatters.py
├── docs/
│   ├── PROJECT_OVERVIEW.md  # 이 파일
│   ├── REQUIREMENTS.md      # 상세 요구사항
│   ├── ARCHITECTURE.md      # 설계 문서
│   └── TODO.md              # 개발 진행 상황
├── pytest.ini
└── README.md
```

## 제약 사항

- BigQuery에 직접 연결하지 않음
- SimpleCatalog를 사용하여 메모리 내에서 테이블 스키마 정의
- BigQuery SQL 방언을 대상으로 함

## 출력 형식

### JSON
```json
{
  "target": {"table": "project.dataset.table", "column": "col1"},
  "parents": [
    {"table": "source1.dataset.table", "column": "src_col1"},
    {"table": "source2.dataset.table", "column": "src_col2"}
  ]
}
```

### 가독성 높은 텍스트
```
project.dataset.table.col1
    <- source1.dataset.table.src_col1
    <- source2.dataset.table.src_col2
```

## 실행 방법

```bash
# 테스트 실행
pytest

# 테이블 리니지 데모
python src/zetasql_demo/examples/demo_table_lineage.py

# 컬럼 리니지 데모
python src/zetasql_demo/examples/demo_column_lineage.py
```
