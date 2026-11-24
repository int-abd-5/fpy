# Graph Report - fpy  (2026-11-25)

## Corpus Check
- 226 files · ~3,858,004 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3427 nodes · 7670 edges · 231 communities (175 shown, 56 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 995 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bcfa3467`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DialogueState
- load_schema
- is_slot_active
- test_validation.py
- QuestionOutput
- test_openai_adapter.py
- FetchResult
- DatasetCandidate
- Forecasting Requirement Elicitation
- dataset_discovery.py
- QuestionRequest
- interfaces/__init__.py
- cli.py
- KeyError
- evaluate_elicitation.py
- http.py
- RegistryApiError
- registry_adapter.py
- DatasetSearchQuery
- RegistryDatasetAdapter
- ValueError
- Image.py
- model_validator
- StrEnum
- RuntimeError
- evaluation/__init__.py
- scripts/__init__.py
- datasets/__init__.py
- forecasting-requirement-elicitation
- Connection
- .__init__
- web.py
- query_from_specification
- DatasetVersion
- config.py
- TiffImagePlugin.py
- SQLiteDialogueRepository
- RegistryClient
- test_render_readiness.py
- Image
- .__init__
- o8
- ValueError
- SQLiteDialogueRepository
- _Operand
- ImageCmsProfile
- FetchResult
- SourcePlan
- .load
- Any
- ImageFile.py
- DeferredError
- ImageOps.py
- Any
- Draw
- ElicitationEngine
- PsdImagePlugin.py
- ImageChops.py
- Window
- GifImagePlugin.py
- ImageFilter.py
- PhotoImage
- BlpImagePlugin.py
- ImagePalette.py
- build_report.py
- ImageFileDirectory_v2
- features.py
- normalize_value
- PngImageFile
- ImageDraw
- Decision records
- PngImagePlugin.py
- openai_responses.py
- AppendingTiffWriter
- LutBuilder
- Jpeg2KImagePlugin.py
- IFDRational
- .transform
- FreeTypeFont
- create_19_section_presentation.mjs
- create_deck.mjs
- AvifImagePlugin.py
- .crop
- ImageFile
- ImageFont
- Any
- Stat
- DdsImagePlugin.py
- new
- PyCodec
- PdfParser.py
- Data Registry Client Integration and Render Readiness
- Execution Flow
- main
- IcnsImagePlugin.py
- TiffImageFile
- PSDraw
- XrefTable
- build_f26_native_latex.py
- build_extractor_input
- Transform
- IndirectReference
- WebPImagePlugin.py
- RegistryClient
- ImagePointTransform
- _Enhance
- ImageFileDirectory_v1
- FakeEngine
- StubHandler
- ContainerIO
- Ghostscript
- PyEncoder
- RankFilter
- ChunkStream
- ExtractorResult
- .load
- GimpGradientFile.py
- IO
- Color3DLUT
- PyDecoder
- run_live_workflows.py
- ForecastingSpecification
- JsonlPipelineLogger
- InMemoryDialogueRepository
- ._bitmap
- GifImageFile
- .get_value
- Project Decisions
- Review Focus
- conditions.py
- FakeHttp
- AnyStr
- Parser
- StubImageFile
- PcfFontFile
- PdfParser
- Review Focus
- NotImplementedError
- ImageQt
- ContainerIO.py
- MpoImageFile
- MspImagePlugin.py
- render_complete_workflow.mjs
- .frombytes
- FpxImageFile
- GimpPaletteFile
- IcoFile
- IcoImageFile
- PdfName
- PpmPlainDecoder
- open
- Global Constraints
- Global Constraints
- RegistryUnavailableError
- open
- IcnsImageFile
- render_user_journey.mjs
- Global Constraints
- Global Constraints
- merge
- MicImageFile
- PdfImagePlugin.py
- _TagInfo
- .__init__
- F26-012 Native LaTeX Report Conversion
- Draw
- FitsImageFile
- .__init__
- fromarrow
- fromqpixmap
- render_motion_walkthrough.mjs
- Catalog discovery path
- Dialogue lifecycle
- F26-012 Deliverable III — author-voice revision
- DdsImageFile
- FtexImageFile
- GbrImageFile
- GribStubImageFile
- HDF5StubImageFile
- getrgb
- .get_variation_axes
- load
- .tobytes
- PpmImageFile
- Extraction and state transition
- F26-012 Deliverable III — LaTeX source
- F26-012 Personal Learning Edition
- F26-012 LaTeX reproduction project
- assemble.py
- F26-012-deliverable-iii/README.md
- _tkinter_finder.py
- DatasetCandidate
- DatasetSearchQuery
- date
- DialogueState
- HttpClient
- Path
- Protocol
- ReadinessReport
- Settings
- SourcePlan
- TraceSink
- BaseModel
- model_validator
- StrEnum
- FetchResult
- asyncio
- FetchResult
- TurnResult

## God Nodes (most connected - your core abstractions)
1. `Image` - 275 edges
2. `load_schema()` - 105 edges
3. `DatasetCandidate` - 83 edges
4. `create_initial_state()` - 71 edges
5. `DatasetSearchQuery` - 68 edges
6. `DialogueState` - 51 edges
7. `QuestionOutput` - 48 edges
8. `_Operand` - 45 edges
9. `o8()` - 45 edges
10. `ImageFileDirectory_v2` - 39 edges

## Surprising Connections (you probably didn't know these)
- `test_build_engine_wires_the_persistent_pipeline_logger()` --uses--> `Settings`  [INFERRED]
  tests/integration/test_cli.py → src/forecasting_assistant/config.py
- `test_interview_uses_one_asyncio_loop_for_all_turns()` --uses--> `TurnResult`  [INFERRED]
  tests/integration/test_cli.py → src/forecasting_assistant/domain/models.py
- `_build_engine()` --calls--> `get_settings()`  [INFERRED]
  scripts/run_live_workflows.py → src/forecasting_assistant/config.py
- `_build_engine()` --calls--> `load_schema()`  [INFERRED]
  scripts/run_live_workflows.py → src/forecasting_assistant/domain/schema.py
- `_build_engine()` --calls--> `PersistentOpenAIResponsesClient`  [INFERRED]
  scripts/run_live_workflows.py → src/forecasting_assistant/infrastructure/llm/openai_responses.py

## Import Cycles
- 3-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/ImageCms.py -> tmp/latex_python/PIL/ImageWin.py -> tmp/latex_python/PIL/Image.py`
- 3-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/JpegImagePlugin.py -> tmp/latex_python/PIL/MpoImagePlugin.py -> tmp/latex_python/PIL/Image.py`
- 3-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/PngImagePlugin.py -> tmp/latex_python/PIL/ImageChops.py -> tmp/latex_python/PIL/Image.py`
- 3-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/PngImagePlugin.py -> tmp/latex_python/PIL/ImageSequence.py -> tmp/latex_python/PIL/Image.py`
- 3-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 4-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/ImageFile.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 4-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/JpegImagePlugin.py -> tmp/latex_python/PIL/MpoImagePlugin.py -> tmp/latex_python/PIL/ImageSequence.py -> tmp/latex_python/PIL/Image.py`
- 4-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/JpegImagePlugin.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 5-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/ImageQt.py -> tmp/latex_python/PIL/ImageFile.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 5-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/JpegImagePlugin.py -> tmp/latex_python/PIL/ImageFile.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 5-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/JpegImagePlugin.py -> tmp/latex_python/PIL/MpoImagePlugin.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 5-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/PngImagePlugin.py -> tmp/latex_python/PIL/ImageFile.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`
- 5-file cycle: `tmp/latex_python/PIL/Image.py -> tmp/latex_python/PIL/PpmImagePlugin.py -> tmp/latex_python/PIL/ImageFile.py -> tmp/latex_python/PIL/TiffImagePlugin.py -> tmp/latex_python/PIL/ImageOps.py -> tmp/latex_python/PIL/Image.py`

## Communities (231 total, 56 thin omitted)

### Community 0 - "DialogueState"
Cohesion: 0.10
Nodes (62): _candidate_status(), catalog_dataset_detail_deferred(), catalog_dataset_schema_deferred(), ClarificationCandidate, evaluate_readiness(), intermediate_core_slot_ids(), _intermediate_unresolved_slots(), _is_required() (+54 more)

### Community 1 - "load_schema"
Cohesion: 0.12
Nodes (51): fixture, apply_extraction(), DialogueTurn, create_initial_state(), load_schema(), test_initial_state_contains_every_slot_as_unmentioned(), test_schema_has_unique_ids_and_approved_version(), test_schema_protects_representative_slot_metadata() (+43 more)

### Community 2 - "is_slot_active"
Cohesion: 0.32
Nodes (16): is_slot_active(), _state(), test_activation_normalizes_case_sensitive_enum_values(), test_all_sub_daily_aliases_activate_timezone(), test_boolean_like_values_activate_and_deactivate_dependents(), test_calendar_duration_aliases_compare_by_period_and_canonical_unit(), test_every_schema_activation_rule_has_expected_positive_case(), test_fixed_duration_magnitude_equivalence_does_not_activate_aggregation() (+8 more)

### Community 3 - "test_validation.py"
Cohesion: 0.12
Nodes (41): _column_values(), _datetime(), _datetime_order_issue(), is_unusable_reference(), _issue(), _number(), _outside_range(), Any (+33 more)

### Community 4 - "QuestionOutput"
Cohesion: 0.23
Nodes (42): asyncio, FakeLLMClient, QuestionOutput, _complete_result(), ExtractorResult, parametrize, SlotStatus, SlotUpdate (+34 more)

### Community 5 - "test_openai_adapter.py"
Cohesion: 0.13
Nodes (30): MonkeyPatch, SimpleNamespace, OpenAIResponsesClient, InjectedClient, PersistentChatInjectedClient, PersistentInjectedClient, asyncio, _question_request() (+22 more)

### Community 6 - "FetchResult"
Cohesion: 0.09
Nodes (25): DatasetSourceAdapter, AcquisitionMode, FetchResult, LicenseAssessment, _candidate(), international_catalog_adapters(), LocalUploadAdapter, _matches() (+17 more)

### Community 7 - "DatasetCandidate"
Cohesion: 0.22
Nodes (14): DatasetRanker, _frequency_unit(), _geography_matches(), ranking_sort_key(), Fail-closed eligibility and deterministic source ranking., _tokens(), DatasetCandidate, RankingBreakdown (+6 more)

### Community 8 - "Forecasting Requirement Elicitation"
Cohesion: 0.13
Nodes (15): Architecture and decision documentation, Deploy the FYP web service on Render, Forecast Specification and Dataset Handoff, Forecasting Requirement Elicitation, Interactive CLI, Intermediate Interview Boundary, Pipeline, Privacy and Secrets (+7 more)

### Community 9 - "dataset_discovery.py"
Cohesion: 0.12
Nodes (16): DatasetCandidateNotSelectableError, DatasetDiscoveryService, DatasetPlanNotFoundError, DatasetSelectionNotFoundError, KeyError, UUID, ValueError, Store a normalized derivative without overwriting its immutable raw parent. (+8 more)

### Community 10 - "QuestionRequest"
Cohesion: 0.21
Nodes (21): QuestionRequest, build_question_input(), _contains_phrase(), _context_value(), _contextual_example(), _duration_unit(), example_answer(), validate_question() (+13 more)

### Community 12 - "cli.py"
Cohesion: 0.13
Nodes (28): callback, command, DatasetDiscoveryService, ElicitationEngine, SQLiteDialogueRepository, build_dataset_service(), build_engine(), _compose_trace_sinks() (+20 more)

### Community 14 - "evaluate_elicitation.py"
Cohesion: 0.23
Nodes (15): build_scenarios(), _case(), main(), Any, validate_scenarios(), compute_metrics(), _divide(), evaluate() (+7 more)

### Community 15 - "http.py"
Cohesion: 0.18
Nodes (9): HTTPRedirectHandler, Request, Any, ValueError, SecureHttpClient, UnsafeDatasetUrlError, validate_public_https_url(), _ValidatedRedirectHandler (+1 more)

### Community 16 - "RegistryApiError"
Cohesion: 0.17
Nodes (11): _clean_payload(), _is_local_host(), _normalize_base_url(), Any, Protocol, RegistryTraceSink, RuntimeError, The registry returned an invalid or non-successful API response. (+3 more)

### Community 17 - "registry_adapter.py"
Cohesion: 0.20
Nodes (14): DatasetPayloadValidationError, _json_point_count(), Any, ValueError, validate_dataset_payload(), QualityReport, _as_optional_string(), _canonical_registry_target() (+6 more)

### Community 18 - "DatasetSearchQuery"
Cohesion: 0.35
Nodes (13): DatasetSearchQuery, _candidate(), FakeAdapter, parametrize, Path, _service(), test_discovery_returns_only_top_three_and_isolates_adapter_failures(), test_executable_payload_fails_before_object_storage() (+5 more)

### Community 19 - "RegistryDatasetAdapter"
Cohesion: 0.24
Nodes (13): KeyError, RegistryDatasetAdapter, FakeHttp, FakeRegistryClient, Any, _source(), test_configured_registry_replaces_remote_catalog_adapters_but_keeps_local_uploads(), test_describe_returns_cached_candidate_by_stable_registry_slug() (+5 more)

### Community 21 - "Image.py"
Cohesion: 0.03
Nodes (60): RuntimeWarning, Format, IntEnum, A Pillow loader for .ftc and .ftu files (FTEX) Jerome Leclanche…, _decompression_bomb_check(), DecompressionBombError, DecompressionBombWarning, getmodebandnames() (+52 more)

### Community 34 - ".__init__"
Cohesion: 0.33
Nodes (3): BaseHTTPRequestHandler, HTTPStatus, DashboardServer

### Community 35 - "web.py"
Cohesion: 0.15
Nodes (22): Connection, _connect(), dashboard_html(), _extract_uploaded_columns(), _json_default(), _list_table(), Any, DialogueState (+14 more)

### Community 36 - "query_from_specification"
Cohesion: 0.29
Nodes (10): _date(), _duration_text(), Any, ForecastingSpecification, query_from_specification(), _string_list(), _text_value(), test_query_from_specification_preserves_prompt_separately_from_registry_target() (+2 more)

### Community 37 - "DatasetVersion"
Cohesion: 0.08
Nodes (14): BaseModel, DatasetSelection, DatasetVersion, SourcePlan, DatasetCatalogRepository, UUID, Connection, Path (+6 more)

### Community 38 - "config.py"
Cohesion: 0.31
Nodes (6): BaseSettings, get_settings(), Settings, ApprovedFutureSource, test_settings_accept_an_explicit_model_name(), test_settings_default_model_allows_dataset_only_commands()

### Community 39 - "TiffImagePlugin.py"
Cohesion: 0.05
Nodes (44): i16be(), i32be(), deprecate(), Deprecations helper. :param deprecated: Name of thing to be deprecated. :param…, _accept(), __getattr__(), Any, # FIXME: I get different results for the same data w. different (+36 more)

### Community 40 - "SQLiteDialogueRepository"
Cohesion: 0.24
Nodes (6): Any, BaseModel, Connection, Path, UUID, SQLiteDialogueRepository

### Community 42 - "test_render_readiness.py"
Cohesion: 0.36
Nodes (9): Run the web interface; PORT is used automatically when provided by Render., web(), run_web_server(), _settings(), test_cli_dataset_service_passes_settings_to_adapter_factory(), test_healthz_reports_app_and_registry_status_without_secrets(), test_required_registry_failure_returns_service_unavailable(), test_web_dashboard_uses_registry_configured_adapters() (+1 more)

### Community 43 - "Image"
Cohesion: 0.03
Nodes (47): PrettyPrinter, IO, _save(), IO, _save(), IO, _save(), blend() (+39 more)

### Community 45 - "o8"
Cohesion: 0.05
Nodes (37): o16le(), o8(), BmpRleDecoder, _dib_save(), IO, _save(), DdsRgbDecoder, FitsGzipDecoder (+29 more)

### Community 46 - "ValueError"
Cohesion: 0.08
Nodes (12): model_validator, This operation will destroy the image core and release its memory. The image…, Exception, IO, Given an rgb tuple, allocate palette entry. .. warning:: This method is…, Save palette to text file. .. warning:: This method is experimental., IO, _save() (+4 more)

### Community 48 - "_Operand"
Cohesion: 0.06
Nodes (22): FontFile, puti16(), BinaryIO, Write network order (big-endian) 16-bit sequence, Base class for raster font file handlers., Create metrics and bitmap, eval(), imagemath_convert() (+14 more)

### Community 49 - "ImageCmsProfile"
Cohesion: 0.06
Nodes (47): CmsProfile, _CmsProfileCompatible, SupportsFloat, SupportsInt, applyTransform(), buildProofTransform(), buildTransform(), createProfile() (+39 more)

### Community 52 - ".load"
Cohesion: 0.05
Nodes (27): Dither, CapsuleType, Convert the image to 'P' mode with the specified number of colors. :param…, Copies this image. Use this method if you wish to paste things into an image,…, Filters this image using the given filter. For a list of available filters, see…, Returns a tuple containing the name of each band in this image. For example,…, Calculates the bounding box of the non-zero regions in the image. :param…, Returns a list of colors used in this image. The colors will be in the image's… (+19 more)

### Community 53 - "Any"
Cohesion: 0.07
Nodes (29): DisplayViewer, EogViewer, GmDisplayViewer, IPythonViewer, MacViewer, Any, Save to temporary file and return filename., Display the given image. (+21 more)

### Community 54 - "ImageFile.py"
Cohesion: 0.07
Nodes (23): i16le(), i32le(), Converts a 2-bytes (16 bits) string to an unsigned integer. :param c: string…, Converts a 2-bytes (16 bits) string to a signed integer. :param c: string…, Converts a 4-bytes (32 bits) string to an unsigned integer. :param c: string…, Converts a 4-bytes (32 bits) string to a signed integer. :param c: string…, si16le(), si32le() (+15 more)

### Community 55 - "DeferredError"
Cohesion: 0.06
Nodes (26): _accept(), DcxImageFile, FliImageFile, isImageType(), Checks if an object is an image object. .. warning:: This function is for…, align8to32(), Any, converts each scanline of data from 8 bit to 32 bit aligned (+18 more)

### Community 56 - "ImageOps.py"
Cohesion: 0.06
Nodes (44): Transpose, autocontrast(), _border(), _color(), colorize(), contain(), cover(), crop() (+36 more)

### Community 57 - "Any"
Cohesion: 0.07
Nodes (13): _ExifBase, Exif, Any, StrOrBytesPath, Returns a dictionary containing the XMP tags. Requires defusedxml to be…, Returns the image palette as a list. :param rawmode: The mode in which to…, If a P mode image has a "transparency" key in the info dictionary, remove the…, Saves this image under the given filename. If no format is specified, the… (+5 more)

### Community 58 - "Draw"
Cohesion: 0.10
Nodes (23): Brush, Draw, Font, Pen, Any, AnyStr, BinaryIO, Coords (+15 more)

### Community 59 - "ElicitationEngine"
Cohesion: 0.14
Nodes (11): QuestionRequest, DialogueNotFoundError, ElicitationEngine, Any, DialogueState, ForecastingSpecification, ReadinessReport, TurnResult (+3 more)

### Community 60 - "PsdImagePlugin.py"
Cohesion: 0.08
Nodes (22): i8(), Converts a 2-bytes (16 bits) string to a signed integer, big endian. :param c:…, Converts a 4-bytes (32 bits) string to a signed integer, big endian. :param c:…, si16be(), si32be(), getOpenProfile(), (pyCMS) Opens an ICC profile file. The PyCMSProfile object can be passed back…, _encode_tile() (+14 more)

### Community 61 - "ImageChops.py"
Cohesion: 0.05
Nodes (36): add(), add_modulo(), blend(), composite(), darker(), difference(), duplicate(), hard_light() (+28 more)

### Community 62 - "Window"
Cohesion: 0.06
Nodes (16): Dib, HDC, HWND, ImageWindow, Same as expose, but allows you to specify where to draw the image, and what…, Installs the palette associated with the image in the given device context.…, Paste a PIL image into the bitmap image. :param im: A PIL image. The size must…, Load display memory contents from byte data. :param buffer: A buffer containing… (+8 more)

### Community 63 - "GifImagePlugin.py"
Cohesion: 0.12
Nodes (35): _Frame, _get_background(), _get_color_table_size(), _get_global_header(), _get_header_palette(), get_interlace(), _get_optimize(), _get_palette_bytes() (+27 more)

### Community 64 - "ImageFilter.py"
Cohesion: 0.09
Nodes (24): BLUR, BoxBlur, BuiltinFilter, CONTOUR, DETAIL, EDGE_ENHANCE, EDGE_ENHANCE_MORE, EMBOSS (+16 more)

### Community 65 - "PhotoImage"
Cohesion: 0.07
Nodes (18): BitmapImage, _get_image_from_kw(), getimage(), PhotoImage, Any, CapsuleType, _pyimagingtkcall(), Get the Tkinter photo image identifier. This method is automatically called by… (+10 more)

### Community 66 - "BlpImagePlugin.py"
Cohesion: 0.10
Nodes (22): _accept(), AlphaEncoding, BLP1Decoder, BLP2Decoder, _BLPBaseDecoder, BLPEncoder, BLPFormatError, BlpImageFile (+14 more)

### Community 67 - "ImagePalette.py"
Cohesion: 0.08
Nodes (17): ImagePalette, negative(), setter, random(), # FIXME: supports GIMP gradients only, Color palette for palette mapped images :param mode: The mode to use for the…, raw(), sepia() (+9 more)

### Community 68 - "build_report.py"
Cohesion: 0.19
Nodes (30): blocks(), change_once(), chapter(), conclusion(), design(), figure(), front_matter(), glossary() (+22 more)

### Community 69 - "ImageFileDirectory_v2"
Cohesion: 0.11
Nodes (10): _IFDv2Base, _LoaderFunc, _accept(), ImageFileDirectory_v2, NoReturn, setter, This class represents a TIFF tag directory. To speed things up, we don't decode…, Initialize an ImageFileDirectory. To construct an ImageFileDirectory from a… (+2 more)

### Community 70 - "features.py"
Cohesion: 0.12
Nodes (27): check(), check_codec(), check_feature(), check_module(), get_supported(), get_supported_codecs(), get_supported_features(), get_supported_modules() (+19 more)

### Community 71 - "normalize_value"
Cohesion: 0.15
Nodes (25): SlotDefinition, _duration_from_text(), _duration_unit_from_text(), _enum_key(), extract_explicit_forecast_horizon(), extract_explicit_frequency(), is_iana_timezone(), _items() (+17 more)

### Community 72 - "PngImageFile"
Cohesion: 0.08
Nodes (15): str, _accept(), iTXt, PngImageFile, PngInfo, Any, internal: finished reading image data, Subclass of string to allow iTXt chunks to look like strings while keeping… (+7 more)

### Community 73 - "ImageDraw"
Cohesion: 0.17
Nodes (13): _Ink, _Outline, _compute_regular_polygon_vertices(), ImageDraw, Coords, Generate a list of vertices for a 2D regular polygon. :param bounding_circle:…, Draw a circle given center coordinates and a radius., Draw a line, or a connected sequence of line segments. (+5 more)

### Community 74 - "Decision records"
Cohesion: 0.07
Nodes (27): D-001 — Hybrid LLM plus deterministic pipeline, D-002 — Schema and SQLite state are authoritative, D-003 — Evidence-bound extraction, D-004 — Persistent provider context is a pilot, not the source of truth, D-005 — Intermediate useful brief, D-006 — Catalog facts are deferred until dataset selection, D-007 — Generated questions are bounded and have a deterministic fallback, D-008 — Explicit confirmation gates the handoff (+19 more)

### Community 75 - "PngImagePlugin.py"
Cohesion: 0.14
Nodes (19): o16be(), o32be(), Blend, _crc32(), Disposal, _fdat, _Frame, getchunks() (+11 more)

### Community 76 - "openai_responses.py"
Cohesion: 0.13
Nodes (14): AsyncOpenAI, Exception, RuntimeError, LLMContractError, PersistentOpenAIResponsesClient, Any, TraceSink, UUID (+6 more)

### Community 78 - "LutBuilder"
Cohesion: 0.09
Nodes (13): LutBuilder, MorphOp, string_permute takes a pattern and a permutation and returns the string…, pattern_permute takes a basic pattern and its result and clones the pattern…, Compile all patterns into a morphology lut. TBD :Build based on (file)…, A class for binary morphological operators, Create a binary morphological operator, Get a list of coordinates matching the morphological operation on an image.… (+5 more)

### Community 79 - "Jpeg2KImagePlugin.py"
Cohesion: 0.12
Nodes (13): BoxReader, Jpeg2KImageFile, _parse_codestream(), _parse_jp2_header(), IO, PixelAccess, setter, Parse the JPEG 2000 codestream to extract the size and component count from the… (+5 more)

### Community 80 - "IFDRational"
Cohesion: 0.14
Nodes (10): Fraction, IntegralLike, Rational, IFDRational, _limit_rational(), _limit_signed_rational(), Implements a rational class where 0/0 is a legal value to match the in the wild…, :param value: either an integer numerator, a float/rational/other number, or an… (+2 more)

### Community 81 - ".transform"
Cohesion: 0.09
Nodes (14): ImageTransformHandler, IntEnum, Protocol, Quantize, Configures the image file loader so it returns a version of the image that as…, Expands the box so it includes adjacent pixels that may be used by resampling…, Returns a rotated copy of this image. This method returns a copy of this image,…, Make this image into a thumbnail. This method modifies the image to contain a… (+6 more)

### Community 82 - "FreeTypeFont"
Cohesion: 0.12
Nodes (16): FreeTypeFont, Layout, load_default(), load_default_imagefont(), BinaryIO, IntEnum, StrOrBytesPath, If FreeType support is available, load a version of Aileron Regular,… (+8 more)

### Community 83 - "create_19_section_presentation.mjs"
Cohesion: 0.15
Nodes (19): arrow(), buildDir, C, candidatePath, chrome(), finalPath, main(), outputDir (+11 more)

### Community 84 - "create_deck.mjs"
Cohesion: 0.15
Nodes (18): addArchitectureArrow(), addPageChrome(), addTitle(), buildDir, bulletList(), C, draftPath, finalPath (+10 more)

### Community 85 - "AvifImagePlugin.py"
Cohesion: 0.14
Nodes (12): AvifImageFile, _get_default_max_threads(), IO, PixelAccess, _save(), _save_all(), Base, GPS (+4 more)

### Community 86 - ".crop"
Cohesion: 0.10
Nodes (12): alpha_composite(), _apply_env_variables(), ImagingCore, NumpyArray, setter, Returns a rectangular region from this image. The box is a 4-tuple defining the…, Returns a rectangular region from the core image object im. This is equivalent…, Returns the contents of this image as a sequence object containing pixel… (+4 more)

### Community 87 - "ImageFile"
Cohesion: 0.11
Nodes (13): fromqimage(), QImage, Creates an image instance from a QImage image, ImageFile, Any, Base class for image file format handlers., Closes the file pointer, if possible. This operation will destroy the image…, fromqimage() (+5 more)

### Community 88 - "ImageFont"
Cohesion: 0.20
Nodes (10): Any, AnyStr, Get the current default font. To set the default font for this ImageDraw…, Get the length of a given string, in pixels with 1/64 precision., Get the bounding box of a given string, in pixels., ImageFont, IO, Wrapper for writing rotated or mirrored text (+2 more)

### Community 89 - "Any"
Cohesion: 0.12
Nodes (10): Any, ImagingCore, Create a bitmap for the text. If the font uses antialiasing, the bitmap should…, Returns bounding box (in pixels) of given text. .. versionadded:: 9.2.0 :param…, Returns length (in pixels) of given text. This is the amount by which following…, Returns length (in pixels with 1/64 precision) of given text when rendered in…, Returns bounding box (in pixels) of given text relative to given anchor when…, Create a bitmap for the text. If the font uses antialiasing, the bitmap should… (+2 more)

### Community 90 - "Stat"
Cohesion: 0.10
Nodes (11): Squared sum of all pixels for each band in the image., Average (arithmetic mean) pixel level for each band in the image., Median pixel level for each band in the image., RMS (root-mean-square) for each band in the image., Variance for each band in the image., Standard deviation for each band in the image., Calculate statistics for the given image. If a mask is included, only the…, Min/max values for each band in the image. .. note:: This relies on the… (+3 more)

### Community 91 - "DdsImagePlugin.py"
Cohesion: 0.15
Nodes (15): o32le(), D3DFMT, DDPF, DDSCAPS, DDSCAPS2, DDSD, DXGI_FORMAT, IntEnum (+7 more)

### Community 92 - "new"
Cohesion: 0.12
Nodes (16): _check_size(), frombuffer(), frombytes(), getmodebase(), new(), Adds or replaces the alpha layer in this image. If the image does not have an…, Attaches a palette to this image. The image must be a "P", "PA", "L" or "LA"…, Gets the "base" mode for given mode. This function returns "L" for images that… (+8 more)

### Community 93 - "PyCodec"
Cohesion: 0.11
Nodes (11): ImagingCore, IO, StrOrBytesPath, PyCodec, PyCodecState, Reads large blocks in a safe way. Unlike fp.read(n), this function doesn't…, Override to perform codec specific initialization :param args: Tuple of arg…, Override to perform codec specific cleanup :returns: None (+3 more)

### Community 94 - "PdfParser.py"
Cohesion: 0.15
Nodes (10): _DictBase, struct_time, decode_text(), encode_text(), pdf_repr(), PdfArray, PdfBinary, PdfDict (+2 more)

### Community 95 - "Data Registry Client Integration and Render Readiness"
Cohesion: 0.11
Nodes (18): Acceptance criteria, Architecture, Configuration, Data Registry Client Integration and Render Readiness, Documentation deliverables, Existing contract, Failure behavior, Fetch behavior (+10 more)

### Community 96 - "Execution Flow"
Cohesion: 0.11
Nodes (19): CLI commands, Confirmation and specification handoff, Dataset selection and fetch, Debugging checkpoints, Deliverable III author-voice document build (2026-11-22), Deliverable III LaTeX report flow, Entry points and initialization, Error and fallback paths (+11 more)

### Community 97 - "main"
Cohesion: 0.26
Nodes (17): add_body(), add_bullet(), add_heading_without_number(), add_scope_item(), main(), Document, remove_bibliography_building_block(), add_body() (+9 more)

### Community 98 - "IcnsImagePlugin.py"
Cohesion: 0.18
Nodes (13): _accept(), IcnsFile, nextheader(), IO, fobj is a file-like object as an icns resource, Get an icon resource as {channel: array}. Note that the arrays are bottom-up…, Saves the image as a series of PNG files, that are then combined into a .icns…, Read a 32bit RGB icon resource. Seems to be either uncompressed or an RLE… (+5 more)

### Community 99 - "TiffImageFile"
Cohesion: 0.13
Nodes (9): PixelAccess, Returns an :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v1` instance with…, Open the first image in a TIFF file, Select a given frame as current image, Return the current frame number, Returns a dictionary of Photoshop "Image Resource Blocks". The keys are the…, Overload method triggered when we detect a compressed tiff Calls out to libtiff, Setup this image object based on current tags (+1 more)

### Community 100 - "PSDraw"
Cohesion: 0.11
Nodes (10): PSDraw, IO, Draw a PIL image, centered in the given box., Sets up printing to the given file. If ``fp`` is omitted, ``sys.stdout.buffer``…, Set up printing of a document. (Write PostScript DSC header.), Ends printing. (Write PostScript DSC footer.), Selects which font to use. :param font: A PostScript font name :param size:…, Draws a line between the two points. Coordinates are given in PostScript point… (+2 more)

### Community 101 - "XrefTable"
Cohesion: 0.14
Nodes (6): mmap, PdfFormatError, IO, RuntimeError, An error that probably indicates a syntactic or semantic error in the PDF file…, XrefTable

### Community 102 - "build_f26_native_latex.py"
Cohesion: 0.28
Nodes (16): PdfReader, block_to_tex(), body_tex(), compact(), create_front_matter(), figure_tex(), main(), preprocess_pages() (+8 more)

### Community 103 - "build_extractor_input"
Cohesion: 0.23
Nodes (15): build_extractor_input(), _context_slot(), _is_secret_key(), Any, _redact_text(), safe_provider_value(), _stable_sort_key(), parametrize (+7 more)

### Community 104 - "Transform"
Cohesion: 0.13
Nodes (14): AffineTransform, ExtentTransform, MeshTransform, PerspectiveTransform, Any, QuadTransform, Define a quad image transform. Maps a quadrilateral (a region defined by four…, Define a mesh image transform. A mesh transform consists of one or more… (+6 more)

### Community 105 - "IndirectReference"
Cohesion: 0.18
Nodes (4): IndirectObjectDef, IndirectReference, IndirectReferenceTuple, NamedTuple

### Community 106 - "WebPImagePlugin.py"
Cohesion: 0.19
Nodes (7): _convert_frame(), Any, IO, PixelAccess, _save(), _save_all(), WebPImageFile

### Community 107 - "RegistryClient"
Cohesion: 0.32
Nodes (13): RegistryClient, RegistryResponse, FakeTransport, Any, test_health_can_disable_retries_for_fast_platform_probes(), test_health_requires_status_ok_and_db_ok(), test_malformed_json_and_response_shape_raise_registry_api_error(), test_non_local_http_registry_url_is_rejected() (+5 more)

### Community 108 - "ImagePointTransform"
Cohesion: 0.14
Nodes (6): _getscaleoffset(), ImagePointHandler, ImagePointTransform, Maps this image through a lookup table or function. :param lut: A lookup table,…, Used as a mixin by point transforms (for use with…, Used with :py:meth:`~PIL.Image.Image.point` for single band images with more…

### Community 109 - "_Enhance"
Cohesion: 0.13
Nodes (10): Brightness, Color, Contrast, _Enhance, Adjust image sharpness. This class can be used to adjust the sharpness of an…, Returns an enhanced image. :param factor: A floating point value controlling…, Adjust image color balance. This class can be used to adjust the colour balance…, Adjust image contrast. This class can be used to control the contrast of an… (+2 more)

### Community 110 - "ImageFileDirectory_v1"
Cohesion: 0.14
Nodes (6): _delegate(), ImageFileDirectory_v1, Any, This class represents the **legacy** interface to a TIFF tag directory. Exposes…, Returns an :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v2` instance with…, :returns: dict of name|key: value Returns the complete tag dictionary, with…

### Community 111 - "FakeEngine"
Cohesion: 0.20
Nodes (8): FakeEngine, UUID, test_build_engine_wires_the_persistent_pipeline_logger(), test_catalog_confirmation_starts_dataset_recommendation_handoff(), test_interview_prints_one_message_per_turn_and_final_json(), test_interview_uses_one_asyncio_loop_for_all_turns(), test_persistent_interview_selects_persistent_provider_mode(), test_show_and_quit_do_not_call_provider()

### Community 112 - "StubHandler"
Cohesion: 0.15
Nodes (11): _accept(), BufrStubImageFile, Install application-specific BUFR image handler. :param handler: Handler object., register_handler(), Install application-specific GRIB image handler. :param handler: Handler object., register_handler(), Install application-specific HDF5 image handler. :param handler: Handler object., register_handler() (+3 more)

### Community 113 - "ContainerIO"
Cohesion: 0.15
Nodes (4): ContainerIO, A file object that provides read access to a part of an existing file (for…, Move file pointer. :param offset: Offset in bytes. :param mode: Starting…, Get current file pointer. :returns: Offset from start of region, in bytes.

### Community 114 - "Ghostscript"
Cohesion: 0.16
Nodes (10): EpsImageFile, Ghostscript(), has_ghostscript(), ImagingCore, IO, PixelAccess, EPS File Parser for the Python Imaging Library, EPS Writer for the Python Imaging Library. (+2 more)

### Community 115 - "PyEncoder"
Cohesion: 0.18
Nodes (9): ImagingEncoder, _getencoder(), Registers an image encoder. This function should not be used in application…, register_encoder(), PyEncoder, Python implementation of a format encoder. Override this class and add the…, Override to perform the encoding process. :param bufsize: Buffer size.…, If ``pushes_fd`` is ``True``, then this method will be used, and ``encode()``… (+1 more)

### Community 116 - "RankFilter"
Cohesion: 0.15
Nodes (8): MaxFilter, MedianFilter, MinFilter, RankFilter, Create a median filter. Picks the median pixel value in a window with the given…, Create a min filter. Picks the lowest pixel value in a window with the given…, Create a max filter. Picks the largest pixel value in a window with the given…, Create a rank filter. The rank filter sorts all pixels in a window of the given…

### Community 117 - "ChunkStream"
Cohesion: 0.21
Nodes (4): ChunkStream, Fetch a new chunk. Returns header information., Call the appropriate chunk handler, Read and verify checksum

### Community 118 - "ExtractorResult"
Cohesion: 0.23
Nodes (5): ExtractorResult, Protocol, StructuredLLMClient, FakeLLMClient, test_extractor_candidate_value_has_a_typed_strict_schema()

### Community 119 - ".load"
Cohesion: 0.21
Nodes (7): _T_co, _get_oserror(), OSError, PixelAccess, raise_oserror(), Load image data based on tile list, (Hook) Find actual image loader.

### Community 120 - "GimpGradientFile.py"
Cohesion: 0.23
Nodes (8): GimpGradientFile, GradientFile, linear(), IO, File handler for GIMP's gradient format., sine(), sphere_decreasing(), sphere_increasing()

### Community 121 - "IO"
Cohesion: 0.23
Nodes (5): IO, StrOrBytesPath, :param offset: Distance to seek. :param whence: Whether the distance is…, _save(), _save_all()

### Community 122 - "Color3DLUT"
Cohesion: 0.20
Nodes (6): Color3DLUT, Any, NumpyArray, Three-dimensional color lookup table. Transforms 3-channel pixels using the…, Generates new LUT using provided callback. :param size: Size of the table.…, Transforms the table values using provided callback and returns a new LUT with…

### Community 123 - "PyDecoder"
Cohesion: 0.18
Nodes (8): ImagingDecoder, _getdecoder(), Registers an image decoder. This function should not be used in application…, register_decoder(), PyDecoder, Python implementation of a format decoder. Override this class and add the…, Override to perform the decoding process. :param buffer: A bytes object with…, Convenience method to set the internal image from a stream of raw data :param…

### Community 124 - "run_live_workflows.py"
Cohesion: 0.47
Nodes (10): _answer_for_slot(), _build_dataset_service(), _build_engine(), _load_scenarios(), main(), Any, Path, _run_all() (+2 more)

### Community 125 - "ForecastingSpecification"
Cohesion: 0.25
Nodes (5): ForecastingSpecification, DialogueRepository, Any, Protocol, UUID

### Community 126 - "JsonlPipelineLogger"
Cohesion: 0.20
Nodes (6): Durable, redacted observability helpers for the elicitation pipeline., JsonlPipelineLogger, Any, Path, Append one redacted, machine-readable record for every pipeline trace event., test_pipeline_logger_writes_timestamped_redacted_jsonl()

### Community 127 - "InMemoryDialogueRepository"
Cohesion: 0.22
Nodes (6): InMemoryDialogueRepository, Any, UUID, test_attaching_uploaded_file_records_source_and_columns(), test_confirmation_requires_explicit_true(), test_engine_persists_provider_conversation_id_from_persistent_client()

### Community 128 - "._bitmap"
Cohesion: 0.22
Nodes (7): _accept(), BmpImageFile, DibImageFile, Open file, check magic number and read header, Image plugin for the Windows Bitmap format (BMP), Read relevant info about the BMP, Seeks to the given frame in this sequence file. If you seek beyond the end of…

### Community 131 - "Project Decisions"
Cohesion: 0.20
Nodes (7): 2026-11-22 — Deliverable III author-voice edition, D-027 — Final Deliverable III source package, Decision index, Future decision record template, How to maintain this file, Project Decisions, Runtime “why” checklist

### Community 132 - "Review Focus"
Cohesion: 0.20
Nodes (9): Deterministic Interview Pilot Implementation Plan, Global Constraints, Review Focus, Task 1: Capture the baseline, Task 2: Make pending-slot answers authoritative, Task 3: Protect forecast intent and catalog source selection, Task 4: Sanitize confirmed values before registry queries, Task 4b: Recover explicit initial time cues (+1 more)

### Community 133 - "conditions.py"
Cohesion: 0.36
Nodes (9): _duration_semantics(), _duration_unit(), _mentioned(), _multi_geography(), _same_granularity(), _selected_covariates(), _source_reference(), _target_requires_sign_rule() (+1 more)

### Community 134 - "FakeHttp"
Cohesion: 0.31
Nodes (6): FakeHttp, Any, test_ndma_mhvra_and_open_data_pakistan_are_not_automatic_sources(), test_pmd_wis2_core_metadata_is_production_eligible_input(), test_research_catalog_stays_separate(), test_who_adapter_returns_concrete_matching_indicator_endpoint()

### Community 135 - "AnyStr"
Cohesion: 0.27
Nodes (4): AnyStr, Read a line of text. :param n: Number of bytes to read. If omitted, zero or…, Read multiple lines of text. :param n: Number of lines to read. If omitted,…, Read data. :param n: Number of bytes to read. If omitted, zero or negative,…

### Community 136 - "Parser"
Cohesion: 0.24
Nodes (5): Parser, Incremental image parser. This class implements the standard feed/close…, (Consumer) Reset the parser. Note that you can only call this method…, (Consumer) Feed data to the parser. :param data: A string buffer. :exception…, (Consumer) Close the stream. :returns: An image object. :exception OSError: If…

### Community 137 - "StubImageFile"
Cohesion: 0.24
Nodes (5): Base class for stub image loaders. A stub loader is an image loader that can…, StubImageFile, PixelAccess, WmfHandler, WmfStubImageFile

### Community 138 - "PcfFontFile"
Cohesion: 0.40
Nodes (4): PcfFontFile, BinaryIO, Font file plugin for the X11 PCF format., sz()

### Community 140 - "Review Focus"
Cohesion: 0.22
Nodes (8): Global Constraints, Registry Client Integration and Render Readiness Implementation Plan, Review Focus, Task 1: Add registry configuration and HTTP client, Task 2: Implement registry-backed dataset discovery and fetching, Task 3: Wire configuration into CLI/web and add Render health behavior, Task 4: Add Render configuration and deployment documentation, Task 5: Final verification and handoff

### Community 141 - "NotImplementedError"
Cohesion: 0.25
Nodes (5): NotImplementedError, NoReturn, :param axes: A list of values for each axis. :exception OSError: If the font is…, grabclipboard(), make_linear_lut()

### Community 142 - "ImageQt"
Cohesion: 0.28
Nodes (7): QByteArray, Returns a QImage copy of this image, ImageQt, QImage, An PIL image wrapper for Qt. This is a subclass of PyQt's QImage class. :param…, toqimage(), toqpixmap()

### Community 143 - "ContainerIO.py"
Cohesion: 0.22
Nodes (5): IO, Create file object. :param file: Existing file. :param offset: Start of region,…, A file object that provides read access to a given member of a TAR file., Create file object. :param tarfile: Name of TAR file. :param file: Name of…, TarIO

### Community 144 - "MpoImageFile"
Cohesion: 0.28
Nodes (3): MpoImageFile, Any, Transform the instance of JpegImageFile into an instance of MpoImageFile. After…

### Community 145 - "MspImagePlugin.py"
Cohesion: 0.28
Nodes (6): _accept(), MspDecoder, MspImageFile, IO, # NOTE: the encoded length of the line can be 0. This was not, _save()

### Community 146 - "render_complete_workflow.mjs"
Cohesion: 0.25
Nodes (7): errors, logs, output, sampleTimes, transcript, webm, work

### Community 147 - ".frombytes"
Cohesion: 0.29
Nodes (6): bdf_char(), BdfFontFile, BinaryIO, Font file plugin for the X11 BDF format., Loads this image with pixel data from a bytes object. This method is similar to…, grab()

### Community 149 - "GimpPaletteFile"
Cohesion: 0.39
Nodes (3): GimpPaletteFile, IO, File handler for GIMP's palette format.

### Community 150 - "IcoFile"
Cohesion: 0.32
Nodes (4): IcoFile, Get a set of all available icon sizes and color depths., Get an image from the icon, Get an image from frame idx

### Community 151 - "IcoImageFile"
Cohesion: 0.29
Nodes (4): IcoImageFile, PixelAccess, setter, PIL read-only image support for Microsoft Windows .ico files. By default the…

### Community 154 - "open"
Cohesion: 0.25
Nodes (6): open(), IO, PixelAccess, StrOrBytesPath, Load texture from a Quake2 WAL texture file. By default, a Quake2 standard…, WalImageFile

### Community 155 - "Global Constraints"
Cohesion: 0.29
Nodes (6): Forecasting Dialogue Hardening Implementation Plan, Global Constraints, Task 1: Regression Tests for Pending Answers and Source Ordering, Task 2: Deterministic Recovery and Dataset-Aware Validation, Task 3: Traceability and Novice-Friendly Questions, Task 4: Verification

### Community 156 - "Global Constraints"
Cohesion: 0.29
Nodes (6): Global Constraints, Intermediate Interview Boundary Implementation Plan, Task 1: Regression tests for priority context and bounded readiness, Task 2: Implement the intermediate policy, Task 3: Confirmation and documentation, Task 4: Verification

### Community 157 - "RegistryUnavailableError"
Cohesion: 0.33
Nodes (4): The registry could not be reached after bounded retries., RegistryUnavailableError, HealthyRegistryClient, UnavailableRegistryClient

### Community 158 - "open"
Cohesion: 0.29
Nodes (6): GdImageFile, open(), IO, StrOrBytesPath, Image plugin for the GD uncompressed format. Note that this format is not…, Load texture from a GD image file. :param fp: GD file name, or an opened file…

### Community 159 - "IcnsImageFile"
Cohesion: 0.29
Nodes (4): IcnsImageFile, PixelAccess, setter, PIL image support for Mac OS .icns files. Chooses the best resolution, but will…

### Community 160 - "render_user_journey.mjs"
Cohesion: 0.33
Nodes (5): htmlPath, mp4Path, outputDir, webmPath, workDir

### Community 161 - "Global Constraints"
Cohesion: 0.33
Nodes (5): Global Constraints, Ontology-Guided Forecasting Interview Implementation Plan, Task 1: Make the forecasting ontology explicit, Task 2: Apply ontology metadata to selection and re-ranking, Task 3: Verify the reported conversation

### Community 162 - "Global Constraints"
Cohesion: 0.33
Nodes (5): Global Constraints, Persistent Interview Chat and Output Plan, Task 1: Reproduce the current persistent output boundary, Task 2: Implement normal-chat handling and quiet persistent output, Task 3: Verify the complete change

### Community 163 - "merge"
Cohesion: 0.33
Nodes (6): getmodebands(), getmodetype(), merge(), Gets the storage type mode. Given a mode, this function returns a single-layer…, Gets the number of individual bands for this mode. :param mode: Input mode.…, Merge a set of single band images into a new multiband image. :param mode: The…

### Community 165 - "PdfImagePlugin.py"
Cohesion: 0.60
Nodes (5): IO, # FIXME: Should replace ASCIIHexDecode with RunLengthDecode, _save(), _save_all(), _write_image()

### Community 166 - "_TagInfo"
Cohesion: 0.40
Nodes (4): lookup(), NamedTuple, :param tag: Integer tag number :param group: Which…, _TagInfo

### Community 167 - ".__init__"
Cohesion: 0.40
Nodes (4): DialogueRepository, ForecastingSchema, StructuredLLMClient, TraceSink

### Community 168 - "F26-012 Native LaTeX Report Conversion"
Cohesion: 0.40
Nodes (4): Constraints, F26-012 Native LaTeX Report Conversion, Goal, Work plan

### Community 169 - "Draw"
Cohesion: 0.40
Nodes (5): ModuleType, Draw(), getdraw(), :param im: The image to draw in. :param hints: An optional list of hints.…, A simple 2D drawing interface for PIL images. :param im: The image to draw in.…

### Community 171 - ".__init__"
Cohesion: 0.40
Nodes (4): _accept(), IconHeader, NamedTuple, Parse image from file-like object containing ico file data

### Community 172 - "fromarrow"
Cohesion: 0.40
Nodes (4): fromarrow(), An object that has an ``__arrow_c_array__`` method corresponding to the arrow c…, Creates an image with zero-copy shared memory from an object exporting the…, SupportsArrowArrayInterface

### Community 173 - "fromqpixmap"
Cohesion: 0.40
Nodes (4): fromqpixmap(), QPixmap, Returns a QPixmap copy of this image, Creates an image instance from a QPixmap image

### Community 174 - "render_motion_walkthrough.mjs"
Cohesion: 0.50
Nodes (3): htmlPath, webmPath, workDir

### Community 175 - "Catalog discovery path"
Cohesion: 0.50
Nodes (4): 1. Build the query, 2. Search configured adapters, 3. Browser catalog response, Catalog discovery path

### Community 176 - "Dialogue lifecycle"
Cohesion: 0.50
Nodes (4): 1. Start or resume a dialogue, 2. Receive one user message, 3. Short-circuit paths, Dialogue lifecycle

### Community 177 - "F26-012 Deliverable III — author-voice revision"
Cohesion: 0.50
Nodes (3): Build, F26-012 Deliverable III — author-voice revision, Files

### Community 183 - "getrgb"
Cohesion: 0.50
Nodes (4): getcolor(), getrgb(), Same as :py:func:`~PIL.ImageColor.getrgb` for most modes. However, if ``mode``…, Convert a color string to an RGB or RGBA tuple. If the string cannot be parsed,…

### Community 184 - ".get_variation_axes"
Cohesion: 0.50
Nodes (3): Axis, :returns: A list of the axes in a variation font. :exception OSError: If the…, TypedDict

### Community 185 - "load"
Cohesion: 0.50
Nodes (4): load(), load_path(), Load a font file. This function loads a font object from the given bitmap font…, Load font file. Same as :py:func:`~PIL.ImageFont.load`, but searches for a…

### Community 188 - "Extraction and state transition"
Cohesion: 0.67
Nodes (3): 4. Provider extraction, 5. Apply or recover the extraction, Extraction and state transition

## Knowledge Gaps
- **156 isolated node(s):** `buildDir`, `outputDir`, `renderDir`, `candidatePath`, `finalPath` (+151 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Image` connect `Image` to `._bitmap`, `Parser`, `StubImageFile`, `PcfFontFile`, `NotImplementedError`, `ImageQt`, `MspImagePlugin.py`, `.frombytes`, `Image.py`, `IcoFile`, `merge`, `PdfImagePlugin.py`, `TiffImagePlugin.py`, `Draw`, `fromarrow`, `o8`, `ValueError`, `fromqpixmap`, `_Operand`, `ImageCmsProfile`, `.load`, `Any`, `DeferredError`, `ImageOps.py`, `Any`, `Draw`, `PsdImagePlugin.py`, `ImageChops.py`, `Window`, `GifImagePlugin.py`, `PhotoImage`, `BlpImagePlugin.py`, `ImageDraw`, `PngImagePlugin.py`, `LutBuilder`, `Jpeg2KImagePlugin.py`, `.transform`, `AvifImagePlugin.py`, `.crop`, `ImageFile`, `ImageFont`, `Stat`, `DdsImagePlugin.py`, `new`, `PyCodec`, `IcnsImagePlugin.py`, `PSDraw`, `Transform`, `WebPImagePlugin.py`, `ImagePointTransform`, `_Enhance`, `StubHandler`, `Ghostscript`, `IO`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `load_schema()` connect `load_schema` to `DialogueState`, `.__init__`, `is_slot_active`, `QuestionOutput`, `test_openai_adapter.py`, `test_validation.py`, `build_extractor_input`, `normalize_value`, `cli.py`, `ValueError`, `evaluate_elicitation.py`, `run_live_workflows.py`, `InMemoryDialogueRepository`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `ElicitationEngine` connect `ElicitationEngine` to `.__init__`, `web.py`, `QuestionOutput`, `.__init__`, `run_live_workflows.py`, `InMemoryDialogueRepository`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 124 inferred relationships involving `ValueError` (e.g. with `_load_scenarios()` and `query_from_specification()`) actually correct?**
  _`ValueError` has 124 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `load_schema()` (e.g. with `main()` and `evaluate()`) actually correct?**
  _`load_schema()` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `DatasetCandidate` (e.g. with `DatasetDiscoveryService` and `DatasetRanker`) actually correct?**
  _`DatasetCandidate` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `create_initial_state()` (e.g. with `.start_dialogue()` and `seed_world_bank_demo()`) actually correct?**
  _`create_initial_state()` has 67 INFERRED edges - model-reasoned connections that need verification._