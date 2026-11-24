from __future__ import annotations

import copy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from build_proposal_pdf import add_hyperlink, add_reference, copy_num_pr, remove_paragraph, set_text


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path('/private/tmp/fyp-proposal-build.LP4spQ/template/FYP1-D1 Project Proposal Template.docx')
DOCX_OUT = ROOT / 'output' / 'Automated_Tabular_Time_Series_Forecasting_Proposal_Cited.docx'


def add_body(document: Document, text: str):
    paragraph = document.add_paragraph(style='Body Text')
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.add_run(text)
    return paragraph


def add_heading_without_number(document: Document, text: str):
    paragraph = document.add_paragraph(style='Heading 1')
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run(text)
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn('w:numPr'))
    if num_pr is not None:
        p_pr.remove(num_pr)
    return paragraph


def add_bullet(document: Document, text: str, num_pr_template) -> None:
    paragraph = document.add_paragraph(style='List Paragraph')
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing = 1.5
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(copy.deepcopy(num_pr_template))
    paragraph.add_run(text)


def add_scope_item(document: Document, label: str, text: str) -> None:
    label_paragraph = document.add_paragraph(style='Body Text')
    label_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    label_paragraph.paragraph_format.line_spacing = 1.5
    label_paragraph.add_run(label).bold = True
    add_body(document, text)


def remove_bibliography_building_block(document: Document) -> None:
    body = document.element.body
    for sdt in list(body.iter(qn('w:sdt'))):
        gallery = sdt.find(
            './w:sdtPr/w:docPartObj/w:docPartGallery',
            namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'},
        )
        if gallery is not None and gallery.get(qn('w:val')) == 'Bibliographies':
            parent = sdt.getparent()
            if parent is not None:
                parent.remove(sdt)


def main() -> None:
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

    current = document.paragraphs
    abstract_heading = next(p for p in current if p.text == 'Abstract')
    num_pr_template = copy_num_pr(next(p for p in current if p.style.name == 'List Paragraph'))
    for paragraph in list(document.paragraphs):
        if paragraph._element is abstract_heading._element:
            continue
        parent = paragraph._element.getparent()
        if parent is not None and parent.index(paragraph._element) > parent.index(abstract_heading._element):
            remove_paragraph(paragraph)
    remove_bibliography_building_block(document)

    # The template's Heading 1 style carries automatic section numbering.
    # Remove only that numbering while retaining its font and spacing.
    heading_style = document.styles['Heading 1']
    style_p_pr = heading_style._element.pPr
    if style_p_pr is not None:
        style_num_pr = style_p_pr.find(qn('w:numPr'))
        if style_num_pr is not None:
            style_p_pr.remove(style_num_pr)

    add_body(document, 'Automated Tabular Time Series Forecasting is a research-and-development project that aims to simplify the process of creating forecasting models for novice users. The system will allow users to describe their forecasting requirements in natural language and will convert those requirements into a structured forecasting specification. A conversational assistant will ask limited and relevant questions, maintain the dialogue state, validate user-provided information, and confirm the requirements before continuing [1], [2]. The project will also include a separate data-ingestion pipeline that periodically collects data from verified sources, validates it, generates metadata and descriptive tags, and stores it in a central dataset database. The main forecasting pipeline will use this database to recommend suitable datasets according to the user\'s requirements. After dataset selection, the system will perform data preparation, identify relevant columns and possible hierarchical relationships, train and compare forecasting models, and evaluate their performance using time-aware methods. The expected output is a reusable forecasting artifact containing the selected model, configuration, evaluation results, and an optional API endpoint.')

    add_heading_without_number(document, 'Introduction')
    add_body(document, 'Time-series forecasting is used in many areas, including economics, finance, energy, weather, sales, healthcare, and population analysis. However, creating a reliable forecasting model usually requires knowledge of data preparation, target selection, time frequency, forecast horizon, model selection, evaluation metrics, and deployment. This makes the process difficult for users who understand the problem they want to solve but do not have advanced machine-learning knowledge.')
    add_body(document, 'This project proposes a natural-language forecasting assistant that allows a user to describe a forecasting requirement in ordinary language. For example, a user may write, "I want to forecast Pakistan\'s inflation rate for the next five years." The system will extract the important requirements, identify missing information, ask simple clarification questions, and confirm the final forecasting specification.')
    add_body(document, 'The system will use large language model-based requirements elicitation and schema-guided dialogue state tracking. The LLMREI research provides the foundation for generating context-dependent requirements questions [1], while the Schema-Guided Dialogue research supports the use of predefined intents, slots, values, and dialogue state [2]. This will help the system remember previously provided information and reduce repeated or irrelevant questions.')
    add_body(document, 'The project will contain two connected backend pipelines. The first pipeline will collect data from verified and approved sources at scheduled intervals. It will validate the data, record its source and update information, generate tags, and store the dataset and metadata in a central database. The second pipeline will interact with the user, confirm the forecasting requirements, search the internal dataset catalog, recommend suitable datasets, and continue with the forecasting process.')
    add_body(document, 'The project will also investigate grouped and hierarchical forecasting. For example, sales data may contain country, region, store, product, and date columns. The system will attempt to identify such relationships and use them in later forecasting stages. Candidate models may include statistical models, machine-learning models, deep-learning models, AutoML approaches, and selected time-series foundation models. AutoGluon is being considered as an AutoML reference [4], while TimesFM is being considered as a time-series foundation-model benchmark [3].')

    add_heading_without_number(document, 'Goals and Objectives')
    add_body(document, 'The main goal of the project is to develop an automated forecasting assistant that converts a novice user\'s natural-language request into a validated forecasting model and reusable forecasting artifact.')
    add_body(document, 'The objectives are:')
    objectives = [
        'To develop a simple natural-language interface through which users can describe forecasting problems without advanced machine-learning knowledge.',
        'To use LLM-based requirements elicitation and schema-guided dialogue state tracking to extract, preserve, validate, and confirm forecasting requirements [1], [2].',
        'To develop a scheduled data-ingestion pipeline that collects data from verified sources, validates it, generates metadata and tags, and stores it in a central dataset database.',
        'To develop an automated forecasting workflow that supports data preparation, hierarchical or grouped forecasting, model training, model comparison, and time-aware evaluation.',
        'To produce a reusable forecasting artifact containing the selected model, preprocessing configuration, evaluation results, dataset information, and an optional API endpoint.',
    ]
    for objective in objectives:
        add_bullet(document, objective, num_pr_template)

    add_heading_without_number(document, 'Scope of the Project')
    add_scope_item(document, '1. User Interaction and Requirements Elicitation', 'The system will allow users to describe forecasting requirements through natural language. It will identify information such as the forecasting target, location or business entity, forecast horizon, time frequency, data source, and desired output. The system will ask a limited number of simple clarification questions and will confirm the final requirements before continuing.')
    add_scope_item(document, '2. Data Collection and Dataset Catalog', 'The project will support uploaded files, approved online sources, databases, and an internal dataset catalog. A separate data-ingestion pipeline will collect data from verified sources at configurable intervals, such as every five or fifteen minutes. It will validate the data, record its source, version, update time, license, and quality information, and generate tags describing its domain, variables, geographic coverage, time range, frequency, and possible forecasting applications. The main forecasting pipeline will search this catalog and recommend suitable datasets after the user\'s requirements have been confirmed. Dataset-specific questions, such as column selection, will only be asked after a dataset has been selected and inspected.')
    add_scope_item(document, '3. Forecasting, Evaluation, and Output', 'After a dataset is selected, the system will inspect its structure, identify time and target columns, detect grouping or hierarchical relationships, and prepare the data for forecasting. The planned system will compare baseline, statistical, machine-learning, deep-learning, AutoML, and selected foundation-model approaches. Models will be evaluated using time-aware backtesting and suitable forecasting metrics. The final output will be a forecasting artifact and may include an API for use by another application. The project will not guarantee perfect forecast accuracy, scrape unrestricted websites during every request, train a large foundation model from scratch, or replace domain experts in high-risk decisions. Data privacy, licensing, and redistribution restrictions will also be considered.')

    add_heading_without_number(document, 'Initial Study and Work Done so Far')
    add_body(document, 'The project is based on research in automated requirements elicitation, dialogue state tracking, automated machine learning, and time-series forecasting. The LLMREI paper was studied as the foundation for adaptive requirements-elicitation interviews [1]. The Schema-Guided Dialogue paper was studied for structured intent and slot tracking [2]. AutoGluon was considered as an AutoML reference for automated model comparison [4], while the TimesFM paper was considered as a possible time-series foundation-model benchmark [3].')
    add_body(document, 'The current implementation is a Python-based requirements-elicitation and dataset-discovery system. It currently focuses on the conversational and dataset-selection stages rather than the complete model-training pipeline.')
    work_done = [
        'A schema-driven forecasting requirements model containing detailed slots for targets, time information, data sources, output, evaluation, and governance.',
        'Structured extraction of forecasting intent and slot values using an OpenAI-based language-model component.',
        'A deterministic state-management and validation layer that prevents unsupported or hallucinated information from being stored.',
        'A bounded and plain-language interview process that preserves dialogue context and explains questions when required.',
        'A persistent interview prototype, dataset discovery component, catalog-ingestion backend boundary, and web preview supporting file upload, dataset recommendations, and dataset fetching.',
    ]
    for item in work_done:
        add_bullet(document, item, num_pr_template)
    add_body(document, 'The current implementation has established the foundation for the project. The next development stage is to connect the confirmed forecasting specification and selected dataset to data preprocessing, model training, hierarchical forecasting, backtesting, model selection, packaging, and inference.')

    references_heading = add_heading_without_number(document, 'References')
    references_heading.paragraph_format.page_break_before = True
    add_reference(document, 1, 'A. Korn, S. Gorsch, and A. Vogelsang', 'LLMREI: Automating Requirements Elicitation Interviews with LLMs', 'arXiv preprint arXiv:2507.02564, 2025.', 'https://arxiv.org/abs/2507.02564')
    add_reference(document, 2, 'A. Rastogi, X. Zang, S. Sunkara, R. Gupta, and P. Khaitan', 'Schema-Guided Dialogue State Tracking Task at DSTC8', 'arXiv preprint arXiv:2002.01359, 2020.', 'https://arxiv.org/abs/2002.01359')
    add_reference(document, 3, 'A. Das, W. Kong, R. Sen, and Y. Zhou', 'A Decoder-Only Foundation Model for Time-Series Forecasting', 'arXiv preprint arXiv:2310.10688, 2023.', 'https://arxiv.org/abs/2310.10688')
    add_reference(document, 4, 'AutoGluon Contributors', 'AutoGluon: Fast and Accurate ML in 3 Lines of Code', 'GitHub repository.', 'https://github.com/autogluon/autogluon')

    DOCX_OUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(DOCX_OUT)
    print(DOCX_OUT)


if __name__ == '__main__':
    main()
