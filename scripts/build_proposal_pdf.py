from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path('/private/tmp/fyp-proposal-build.LP4spQ/template/FYP1-D1 Project Proposal Template.docx')
DOCX_OUT = ROOT / 'output' / 'Automated_Tabular_Time_Series_Forecasting_Proposal.docx'


def set_text(paragraph, text: str) -> None:
    paragraph.clear()
    paragraph.add_run(text)


def remove_paragraph(paragraph) -> None:
    element = paragraph._element
    element.getparent().remove(element)


def add_body(document: Document, text: str):
    paragraph = document.add_paragraph(style='Body Text')
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.add_run(text)
    return paragraph


def add_heading(document: Document, text: str):
    paragraph = document.add_paragraph(style='Heading 1')
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run(text)
    return paragraph


def add_numbered(document: Document, text: str, num_pr_template) -> None:
    paragraph = document.add_paragraph(style='List Paragraph')
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing = 1.5
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(copy.deepcopy(num_pr_template))
    paragraph.add_run(text)


def copy_num_pr(paragraph):
    return paragraph._p.pPr.find(qn('w:numPr'))


def add_hyperlink(paragraph, text: str, url: str) -> None:
    part = paragraph.part
    relationship_id = part.relate_to(
        url,
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
        is_external=True,
    )
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), relationship_id)
    run = OxmlElement('w:r')
    run_properties = OxmlElement('w:rPr')
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '0563C1')
    run_properties.append(color)
    underline = OxmlElement('w:u')
    underline.set(qn('w:val'), 'single')
    run_properties.append(underline)
    run.append(run_properties)
    text_element = OxmlElement('w:t')
    text_element.text = text
    run.append(text_element)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_reference(document: Document, number: int, authors: str, title: str, details: str, url: str):
    paragraph = document.add_paragraph(style='Body Text')
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.add_run(f'[{number}] {authors}, "{title}," {details} Available: ')
    add_hyperlink(paragraph, url, url)


def main() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)

    document = Document(TEMPLATE)
    paragraphs = document.paragraphs

    set_text(paragraphs[6], 'Automated Tabular Time Series Forecasting')
    set_text(paragraphs[7], 'Project Proposal')
    set_text(paragraphs[11], 'Project Advisor:')
    set_text(paragraphs[12], 'Dr Hajra Waheed')
    set_text(paragraphs[14], 'Group Members:')
    set_text(paragraphs[15], 'Muhammad Abdullah Shahid\t\t23l-0937')
    set_text(paragraphs[16], 'Abdullah Usman\t\t23l-0735')
    set_text(paragraphs[17], 'Uneeb Shahbaz\t\t23l-0789')
    remove_paragraph(paragraphs[18])

    # Keep the template cover and institutional information. Rebuild the body
    # after the existing Abstract heading so that all body text uses template styles.
    current = document.paragraphs
    abstract_heading = next(p for p in current if p.text == 'Abstract')
    num_pr_template = copy_num_pr(next(p for p in current if p.style.name == 'List Paragraph'))
    for paragraph in list(document.paragraphs):
        if paragraph._element is abstract_heading._element:
            continue
        if paragraph._element.getparent() is not None and paragraph._element.getparent().index(paragraph._element) > paragraph._element.getparent().index(abstract_heading._element):
            remove_paragraph(paragraph)
    # The template contains an embedded Word bibliography building block that
    # is not exposed through python-docx's paragraph collection. Remove it so
    # the regenerated references section is the only one in the document.
    body = document.element.body
    for sdt in list(body.iter(qn('w:sdt'))):
        gallery = sdt.find('./w:sdtPr/w:docPartObj/w:docPartGallery', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        if gallery is not None and gallery.get(qn('w:val')) == 'Bibliographies':
            parent = sdt.getparent()
            if parent is not None:
                parent.remove(sdt)

    add_body(document, (
        'Time-series forecasting is an important task in economics, finance, energy, weather, healthcare, and business analytics. '
        'However, conventional forecasting systems usually require users to understand data preparation, time-series structures, '
        'forecasting models, evaluation metrics, and deployment procedures. This creates a significant barrier for novice users who '
        'may understand the business problem but may not know how to convert it into a technically valid forecasting task.'
    ))
    add_body(document, (
        'This project proposes an automated, research-driven time-series forecasting pipeline that allows a user to describe a '
        'forecasting requirement using natural language. The system converts the user description into a structured forecasting '
        'specification containing information such as the forecasting objective, target variable, geographical or business level, '
        'forecast horizon, data source, output requirements, and other relevant requirements. A conversational requirements-'
        'elicitation component asks limited, adaptive, and plain-language questions whenever important information is missing or ambiguous.'
    ))
    add_body(document, (
        'The proposed system combines large language model-based requirements elicitation with schema-guided dialogue state tracking. '
        'The system maintains the state of the conversation, validates extracted information, prevents unsupported assumptions, and '
        'asks for confirmation before proceeding. The user may provide a dataset through file upload or select a suitable dataset '
        'from a trusted internal catalog. After the requirements and dataset are confirmed, the planned pipeline will validate the '
        'data, identify time and target columns, detect possible grouped or hierarchical relationships, prepare the data, train '
        'candidate forecasting models, evaluate them using time-series backtesting, and select a suitable model.'
    ))
    add_body(document, (
        'The system will also include a separate automated data-ingestion pipeline. This pipeline will periodically collect data from '
        'verified and approved sources, validate and normalize the collected data, generate metadata and descriptive tags, and store '
        'the data in a central dataset database. The main forecasting pipeline will query this database when recommending datasets, '
        'instead of scraping external websites during every user request.'
    ))
    add_body(document, (
        'The final system is intended to produce a reusable forecasting artifact containing the trained model, preprocessing '
        'configuration, evaluation results, and an optional API endpoint. The project currently focuses on requirements elicitation, '
        'dialogue-state management, dataset discovery, and the catalog data layer, while the forecasting, model-selection, packaging, '
        'and deployment stages will be developed as subsequent modules. The system aims to reduce the technical effort required to '
        'build a forecasting solution while maintaining traceability, reproducibility, and empirical evaluation of forecasting accuracy.'
    ))

    add_heading(document, 'Introduction')
    add_body(document, (
        'Time-series forecasting is the process of using historical observations to estimate future values. It is used in many '
        'real-world situations, including predicting inflation, energy demand, electricity prices, weather variables, sales, '
        'financial prices, population statistics, and other economic or operational indicators. Although many forecasting libraries '
        'and machine-learning methods are available, using them correctly often requires technical knowledge. A user must usually '
        'identify the time column, target column, data frequency, forecast horizon, relevant grouping variables, missing-value policy, '
        'evaluation method, and suitable forecasting model.'
    ))
    add_body(document, (
        'This project addresses the difficulty of creating forecasting models by allowing a user to describe the forecasting problem '
        'in ordinary language. For example, a user may write, "I want to forecast Pakistan inflation rate for the next five years," '
        'without knowing the exact technical information required by a forecasting framework. The system analyzes the request, '
        'identifies the information already provided, and asks only the most important unanswered questions. The questions are '
        'designed for non-expert users and avoid unnecessary technical terminology.'
    ))
    add_body(document, (
        'The first major component of the project is an automated requirements-elicitation assistant. It uses a large language model '
        'to interpret the user request and generate context-dependent clarification questions. The LLMREI research provides the '
        'foundation for this conversational approach because it investigates the use of large language models for automating '
        'requirements-elicitation interviews and adapting questions according to the conversation context [1]. The proposed system '
        'applies this idea to forecasting requirements.'
    ))
    add_body(document, (
        'The second major component is schema-guided dialogue and state tracking. The system represents the forecasting requirements '
        'as a predefined schema containing named slots, such as forecasting intent, target variable, geographical level, forecast '
        'horizon, time frequency, data source, and output format. Each slot has a status and value. The Schema-Guided Dialogue '
        'research provides the conceptual basis for tracking intents, slots, values, and dialogue state in a structured manner [2]. '
        'This allows the application to preserve information between turns and reduces the possibility of repeatedly asking the same question.'
    ))
    add_body(document, (
        'The project consists of two connected backend pipelines. The first is an automated data-ingestion pipeline responsible for '
        'continuously maintaining the project dataset catalog. It will collect data from verified sources through scheduled source '
        'adapters at a configurable interval, such as every five or fifteen minutes. The collected data will be checked for validity, '
        'freshness, completeness, source reliability, licensing restrictions, and structural consistency before being stored.'
    ))
    add_body(document, (
        'The ingestion pipeline will store both the dataset and its associated metadata. The metadata may include the dataset domain, '
        'source organization, geographic coverage, time coverage, update frequency, available variables, data type, license, data '
        'quality indicators, and possible forecasting applications. Additional tags may indicate whether the dataset is suitable for '
        'univariate forecasting, multivariate forecasting, grouped forecasting, hierarchical forecasting, classification, regression, '
        'or other machine-learning tasks.'
    ))
    add_body(document, (
        'The second pipeline is the main user-facing forecasting pipeline. After the user describes a forecasting requirement and '
        'confirms it, this pipeline will query the internal dataset database using the extracted requirements and metadata tags. It '
        'will rank and recommend the most relevant datasets to the user. The main forecasting pipeline will therefore obtain data '
        'from the maintained database rather than directly searching and scraping the internet during every forecasting request.'
    ))
    add_body(document, (
        'Once a dataset is selected, the system will inspect its structure and identify the time column, target column, numerical '
        'and categorical variables, missing values, and possible relationships between different levels. For example, sales data '
        'may be organized by country, region, store, product, and date. Such structures can support grouped or hierarchical '
        'forecasting, where forecasts at detailed levels can be related to forecasts at broader levels.'
    ))
    add_body(document, (
        'The later stages of the project will include data validation, preprocessing, feature preparation, candidate model training, '
        'backtesting, evaluation, and model selection. Classical statistical models, machine-learning models, deep-learning models, '
        'and selected time-series foundation models may be compared. AutoGluon is being considered as an engineering reference because '
        'it provides automated machine learning capabilities for tabular and time-series data and can compare multiple models '
        'automatically [4]. TimesFM is being considered as a foundation-model benchmark because its research investigates zero-shot '
        'time-series forecasting across different history lengths, prediction lengths, and temporal granularities [3].'
    ))
    add_body(document, (
        'The project is therefore a research-and-development system rather than a simple chatbot. Its purpose is to connect natural-'
        'language requirements elicitation with an automated, traceable, and reproducible forecasting workflow.'
    ))

    add_heading(document, 'Goals and Objectives')
    add_body(document, (
        'The main goal of this project is to develop an automated time-series forecasting assistant that converts a novice user\'s '
        'natural-language request into a validated forecasting model and a reusable forecasting artifact.'
    ))
    add_body(document, 'The objectives of the project are:')
    objectives = [
        'To develop a natural-language interface through which a novice user can describe a forecasting problem without requiring advanced machine-learning knowledge.',
        'To extract important forecasting requirements from a user\'s initial description, including the forecasting objective, target variable, geographical or business scope, forecast horizon, time frequency, data source, and desired output.',
        'To use a schema-guided representation of forecasting requirements so that the system can track which information has been provided, inferred, confirmed, or remains missing.',
        'To develop an adaptive requirements-elicitation process that asks concise and relevant questions instead of repeatedly asking the user for information that has already been provided.',
        'To use simple, user-friendly language and explain technical questions when the user asks what a question means.',
        'To maintain conversational context and preserve the state of a forecasting request across multiple user interactions.',
        'To validate extracted values and prevent unsupported assumptions or hallucinated information from becoming part of the forecasting specification.',
        'To support multiple data-source options, including user-uploaded files, approved online sources, databases, and an internal project data catalog.',
        'To develop a trusted data catalog containing dataset metadata such as domain, variables, location, time coverage, frequency, license, source, and possible forecasting applications.',
        'To recommend suitable catalog datasets after the user\'s forecasting requirements have been confirmed.',
        'To develop a separate scheduled data-ingestion pipeline that collects datasets from verified and approved sources.',
        'To validate, normalize, version, and store collected datasets together with their source information, timestamps, checksums, licensing details, and quality indicators.',
        'To generate searchable metadata and tags describing each dataset\'s domain, variables, geographic coverage, time coverage, frequency, and possible forecasting applications.',
        'To connect the main forecasting pipeline to the internal dataset database so that suitable datasets can be recommended without performing real-time unrestricted web scraping.',
        'To inspect the selected dataset and automatically identify time-related columns, target columns, grouping variables, numerical features, categorical features, missing values, and possible hierarchical relationships.',
        'To support forecasting problems involving multiple levels, such as country, region, store, product, or other related entities.',
        'To develop data-validation and preprocessing procedures for tabular time-series datasets.',
        'To train and compare multiple forecasting models, including baseline, statistical, machine-learning, deep-learning, and selected foundation-model approaches.',
        'To evaluate forecasting models using suitable time-series metrics, including MAE, RMSE, MAPE or sMAPE, MASE, WAPE, prediction-interval coverage, and quantile-based metrics where applicable.',
        'To use rolling-origin or time-aware backtesting instead of random train-test splitting.',
        'To investigate automated model-selection techniques, including AutoML, meta-learning, and LLM-assisted model selection.',
        'To package the selected model, preprocessing steps, configuration, metadata, and evaluation results into a reusable artifact.',
        'To provide an optional API endpoint through which the generated forecasting model can be used by another application or website.',
        'To evaluate the system not only by forecasting accuracy but also by requirement-extraction accuracy, number of dialogue turns, clarification success, confirmation accuracy, usability, and reproducibility.',
    ]
    for objective in objectives:
        add_numbered(document, objective, num_pr_template)

    add_heading(document, 'Scope of the Project')
    add_body(document, (
        'The project focuses on the automation of tabular time-series forecasting for users who may not have advanced knowledge of '
        'forecasting or machine learning. The intended system will accept a natural-language forecasting request and guide the user '
        'through a limited requirements-elicitation process.'
    ))
    add_body(document, (
        'The project will support forecasting tasks from several domains, including economic forecasting such as inflation and '
        'interest rates; financial forecasting such as asset prices and market indicators; energy forecasting such as electricity '
        'demand and power prices; weather and environmental forecasting; sales and demand forecasting; population, health, and '
        'demographic forecasting; and other domains containing structured historical observations with a time component.'
    ))
    add_body(document, (
        'The requirements-elicitation component will collect and validate the main forecasting requirements. These requirements may '
        'include the target to be predicted, the relevant country or region, the business entity, the forecast horizon, the time '
        'frequency, the desired output, the data source, and whether the user wants a single series or multiple related series.'
    ))
    add_body(document, (
        'The project will support user-uploaded datasets, approved online data sources accessed through predefined adapters, '
        'database-based sources where the user supplies an appropriate connection reference, and a project-managed data catalog '
        'containing trusted datasets and metadata.'
    ))
    add_body(document, (
        'The project will contain a separate automated dataset-ingestion service. This service will run on a scheduled basis, with '
        'the interval configured according to the source and project requirements. A typical refresh interval may be five or fifteen '
        'minutes, although slower-changing sources may be updated less frequently.'
    ))
    add_body(document, (
        'The ingestion service will use approved connectors or source adapters to collect data from verified websites, public APIs, '
        'government portals, research repositories, and other authorized sources. Each source must be registered, evaluated, and '
        'associated with appropriate provenance and licensing information before it is used.'
    ))
    add_body(document, (
        'For every collected dataset, the ingestion service will perform basic validation and preparation tasks. These tasks may '
        'include checking the download, verifying the file format, identifying missing or duplicate records, checking timestamps, '
        'detecting schema changes, calculating checksums, recording the retrieval time, and identifying whether the data has been '
        'updated since the previous collection.'
    ))
    add_body(document, (
        'The validated dataset and its metadata will be stored in the central dataset database or associated object storage. Each '
        'dataset record will contain descriptive tags for its domain, source organization, geographic or business coverage, '
        'available variables, time range, time frequency, data type, file format, possible forecasting tasks, possible target '
        'variables, support for single-series or multi-series forecasting, support for grouped or hierarchical forecasting, data '
        'quality, licensing status, retrieval time, update time, dataset version, and checksum.'
    ))
    add_body(document, (
        'When the user selects the project catalog, the system will not ask unnecessary questions about the dataset before a catalog '
        'item has been selected. The system will first complete and confirm the user\'s forecasting requirements. It will then '
        'recommend catalog datasets based on the confirmed requirements. After the user selects a dataset, the system may inspect '
        'its schema and ask only dataset-specific questions that are relevant to the selected data.'
    ))
    add_body(document, (
        'The main forecasting pipeline will use the catalog records to search and rank datasets according to the user\'s confirmed '
        'requirements. The actual dataset will be fetched from the project database or storage layer after the user selects a '
        'recommendation. This architecture separates continuous data collection from user-specific forecasting and improves dataset '
        'provenance and response efficiency.'
    ))
    add_body(document, (
        'The project will include data inspection and schema inference. The system will attempt to identify the time column, target '
        'column, numerical variables, categorical variables, missing values, duplicate timestamps, time frequency, and grouping '
        'columns. It will also investigate possible hierarchical structures, such as country-region-store-product relationships. '
        'Hierarchical forecasting will be treated as an important research direction because forecasts at multiple levels can provide '
        'a broader view of the forecasting problem.'
    ))
    add_body(document, (
        'The planned forecasting pipeline will include data validation, preprocessing, feature engineering, candidate-model training, '
        'time-aware backtesting, model comparison, and model selection. The system may compare simple baselines, statistical '
        'forecasting methods, machine-learning models, deep-learning models, and time-series foundation models. Foundation models '
        'will be used as benchmarks or candidate models; the project will not train a large foundation model from scratch.'
    ))
    add_body(document, (
        'The final planned output will be a forecasting artifact containing the selected model, preprocessing configuration, forecasting '
        'specification, evaluation metrics, dataset metadata, and instructions for use. An optional API may also be generated for '
        'integration with another website or software system.'
    ))
    add_body(document, (
        'The system will not guarantee that every forecast is accurate. Accuracy will depend on the quality, size, completeness, and '
        'predictability of the selected data. It will not automatically scrape arbitrary websites at runtime; dataset retrieval will '
        'be restricted to approved sources and adapters. Data licensing, privacy, and redistribution restrictions must be respected. '
        'The system will not collect passwords, API keys, database credentials, or other secrets as ordinary forecasting requirements. '
        'The project will not attempt to replace a domain expert in high-risk decision-making. The current implementation primarily '
        'covers requirements elicitation, dialogue-state management, dataset discovery, and the catalog handoff; the complete '
        'model-training, evaluation, packaging, and deployment pipeline remains part of the planned development work.'
    ))

    add_heading(document, 'Initial Study and Work Done so Far')
    add_body(document, (
        'The project began with a review of research related to requirements elicitation, dialogue-state tracking, automated machine '
        'learning, and time-series forecasting.'
    ))
    add_body(document, (
        'The LLMREI paper was studied as the main foundation for the requirements-elicitation component. It presents a chatbot-based '
        'approach for automating requirements-elicitation interviews and investigates how large language models can extract '
        'requirements and generate questions that depend on the interview context [1]. This research motivated the use of an LLM to '
        'interpret the user initial forecasting request and ask adaptive clarification questions.'
    ))
    add_body(document, (
        'The Schema-Guided Dialogue State Tracking research was studied as the foundation for the slot-filling and state-management '
        'component [2]. The project applies this idea by defining forecasting intents and slots explicitly. Instead of allowing the '
        'language model to control the entire application state, the model proposes structured information and the application validates '
        'and stores it.'
    ))
    add_body(document, (
        'The project proposal also considered AutoML and forecasting model-selection approaches. AutoGluon is being evaluated as a '
        'practical engineering reference because it supports automated model training and comparison for tabular and time-series data '
        '[4]. The TimesFM research is being considered for a foundation-model benchmark because it investigates a decoder-only '
        'time-series model that can produce forecasts across different history lengths, prediction lengths, and temporal granularities '
        '[3]. Other approaches identified in the proposal include AutoForecast, FLAML, Chronos, LLM-guided model selection, and '
        'traditional statistical forecasting methods.'
    ))
    add_body(document, (
        'The current implementation is a Python-based forecasting requirements and dataset-discovery system. The repository currently '
        'implements the first major milestones rather than the entire forecasting pipeline. The completed work includes the following:'
    ))
    work_done = [
        'A schema-driven forecasting requirements model has been implemented. The schema contains 79 detailed slots covering request information, target details, time information, series structure, data source, data quality, seasonality, covariates, output, evaluation, operations, and governance.',
        'Typed domain models have been created for dialogue state, slot values, validation results, forecasting specifications, dataset candidates, source plans, and dataset selections.',
        'An OpenAI-based structured extraction component has been implemented. It extracts candidate intent and slot updates from user messages while following a defined output structure.',
        'A deterministic state-reduction layer has been implemented. LLM output is treated as untrusted until the application verifies the evidence, values, statuses, and identifiers.',
        'Evidence checking has been implemented so that extracted values must be supported by the current user message. Assistant suggestions are not automatically treated as facts provided by the user.',
        'Normalization has been implemented for common user expressions. Different ways of saying catalog, data list, or a time interval can be mapped to the same internal representation.',
        'A bounded interview policy has been implemented. The system prioritizes the most important unresolved requirements and avoids asking an unnecessarily large number of questions.',
        'The interview uses plain-language questions and can explain a technical question when the user asks what it means. The explanation does not modify the forecasting requirements.',
        'A persistent-context interview pilot has been implemented. It can reuse one provider-side conversation for a dialogue while keeping the local SQLite state authoritative.',
        'Dialogue state, conversation identifiers, specifications, dataset selections, and audit events are persisted locally.',
        'A data-catalog discovery component has been implemented. It can rank suitable dataset candidates according to the user confirmed forecasting requirements and present recommendations before the user selects a dataset.',
        'Dataset selection and fetching procedures have been separated from requirements elicitation so that dataset-column questions are deferred until a catalog dataset has been selected and inspected.',
        'A catalog-ingestion backend has been established as a separate system boundary for approved source adapters, dataset collection, validation, metadata generation, tagging, versioning, and database or object-storage handoff. Its scheduled refresh interval is configurable according to the source and deployment environment.',
        'Local upload support has been added for testing through the web preview. The preview can accept common structured data formats and attach the uploaded file to the dialogue or dataset workflow.',
        'A pipeline logger has been implemented. It records redacted events such as extraction requests, structured responses, state updates, question selection, dataset recommendations, and assistant messages. Sensitive credentials are redacted before storage.',
        'A chat-style web preview has been implemented. It provides a user-facing interface for the persistent interview, file upload, plain-language requirements display, catalog recommendations, and dataset fetching. API traces are hidden from the normal user interface.',
        'Automated tests have been created for the schema, state reducer, validation, normalization, question policy, dialogue flow, dataset discovery, dataset ranking, persistence, logging, OpenAI adapter, CLI, and web interface.',
    ]
    for item in work_done:
        add_numbered(document, item, num_pr_template)
    add_body(document, (
        'The current implementation has therefore established the conversational, dataset-catalog, and data-handoff foundation of '
        'the project. The next major development stage is to connect the confirmed forecasting specification and selected dataset to '
        'the data-validation, preprocessing, model-training, backtesting, model-selection, packaging, and inference stages described '
        'in the original project proposal. The scheduled data-ingestion pipeline will provide the maintained dataset and metadata '
        'layer required by these later forecasting stages.'
    ))

    add_heading(document, 'References')
    add_reference(document, 1, 'A. Korn, S. Gorsch, and A. Vogelsang', 'LLMREI: Automating Requirements Elicitation Interviews with LLMs', 'arXiv preprint arXiv:2507.02564, 2025.', 'https://arxiv.org/abs/2507.02564')
    add_reference(document, 2, 'A. Rastogi, X. Zang, S. Sunkara, R. Gupta, and P. Khaitan', 'Schema-Guided Dialogue State Tracking Task at DSTC8', 'arXiv preprint arXiv:2002.01359, 2020.', 'https://arxiv.org/abs/2002.01359')
    add_reference(document, 3, 'A. Das, W. Kong, R. Sen, and Y. Zhou', 'A Decoder-Only Foundation Model for Time-Series Forecasting', 'arXiv preprint arXiv:2310.10688, 2023.', 'https://arxiv.org/abs/2310.10688')
    add_reference(document, 4, 'AutoGluon Contributors', 'AutoGluon: Fast and Accurate ML in 3 Lines of Code', 'GitHub repository.', 'https://github.com/autogluon/autogluon')

    DOCX_OUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(DOCX_OUT)
    print(DOCX_OUT)


if __name__ == '__main__':
    main()
