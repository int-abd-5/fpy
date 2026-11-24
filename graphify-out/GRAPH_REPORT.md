# Graph Report - fpy  (2026-11-25)

## Corpus Check
- 88 files · ~72,195 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3428 nodes · 7670 edges · 224 communities (164 shown, 60 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 995 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ce7a8bc9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SlotState
- load_schema
- is_slot_active
- validation.py
- QuestionOutput
- test_openai_adapter.py
- FetchResult
- DatasetCandidate
- Forecasting Requirement Elicitation
- ImageFile.py
- ImagePalette
- interfaces/__init__.py
- cli.py
- KeyError
- evaluate_elicitation.py
- http.py
- RegistryClient
- registry_adapter.py
- FakeAdapter
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
- MemoryCatalogRepository
- TiffImagePlugin.py
- ForecastingSpecification
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
- BmpImagePlugin.py
- DeferredError
- ImageOps.py
- Any
- Draw
- ElicitationEngine
- _binary.py
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
- state_reducer.py
- PngImageFile
- ImageDraw
- Decision records
- PngImagePlugin.py
- DialogueState
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
- .__init__
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
- ImagingCore
- ImagePointTransform
- _Enhance
- ImageFileDirectory_v1
- models.py
- StubHandler
- ContainerIO
- EpsImagePlugin.py
- PyEncoder
- RankFilter
- ChunkStream
- BoxReader
- .load
- MultibandFilter
- IO
- Color3DLUT
- PyDecoder
- config.py
- _i
- JsonlPipelineLogger
- UnsharpMask
- ._bitmap
- GifImageFile
- .get_value
- Project Decisions
- Review Focus
- fromqimage
- FakeHttp
- .legacy_api
- Parser
- StubImageFile
- PcfFontFile
- PdfParser
- Review Focus
- NotImplementedError
- ImageQt
- ContainerIO.py
- MpoImagePlugin.py
- SupportsArrayInterface
- render_complete_workflow.mjs
- .frombytes
- FpxImageFile
- GimpPaletteFile
- IcoFile
- Protocol
- PdfName
- PpmPlainDecoder
- open
- Global Constraints
- Global Constraints
- RuntimeError
- GdImageFile.py
- IcnsImageFile
- render_user_journey.mjs
- Global Constraints
- Global Constraints
- MicImageFile
- PdfImagePlugin.py
- _TagInfo
- F26-012 Native LaTeX Report Conversion
- FitsImageFile
- fromarrow
- fromqpixmap
- render_motion_walkthrough.mjs
- Catalog discovery path
- Dialogue lifecycle
- F26-012 Deliverable III — author-voice revision
- FtexImageFile
- GbrImageFile
- GribStubImageFile
- HDF5StubImageFile
- getrgb
- .get_variation_axes
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
- `test_extractor_candidate_value_has_a_typed_strict_schema()` --uses--> `ExtractorResult`  [INFERRED]
  tests/unit/test_openai_adapter.py → src/forecasting_assistant/domain/models.py
- `test_build_engine_wires_the_persistent_pipeline_logger()` --uses--> `Settings`  [INFERRED]
  tests/integration/test_cli.py → src/forecasting_assistant/config.py
- `_build_engine()` --calls--> `load_schema()`  [INFERRED]
  scripts/run_live_workflows.py → src/forecasting_assistant/domain/schema.py
- `_build_engine()` --calls--> `PersistentOpenAIResponsesClient`  [INFERRED]
  scripts/run_live_workflows.py → src/forecasting_assistant/infrastructure/llm/openai_responses.py
- `_build_engine()` --calls--> `JsonlPipelineLogger`  [INFERRED]
  scripts/run_live_workflows.py → src/forecasting_assistant/infrastructure/observability/pipeline_logger.py

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

## Communities (224 total, 60 thin omitted)

### Community 0 - "SlotState"
Cohesion: 0.12
Nodes (52): _candidate_status(), catalog_dataset_detail_deferred(), catalog_dataset_schema_deferred(), ClarificationCandidate, evaluate_readiness(), intermediate_core_slot_ids(), _intermediate_unresolved_slots(), _is_required() (+44 more)

### Community 1 - "load_schema"
Cohesion: 0.12
Nodes (51): fixture, apply_extraction(), DialogueTurn, create_initial_state(), load_schema(), test_initial_state_contains_every_slot_as_unmentioned(), test_schema_has_unique_ids_and_approved_version(), test_schema_protects_representative_slot_metadata() (+43 more)

### Community 2 - "is_slot_active"
Cohesion: 0.29
Nodes (17): KeyError, is_slot_active(), _state(), test_activation_normalizes_case_sensitive_enum_values(), test_all_sub_daily_aliases_activate_timezone(), test_boolean_like_values_activate_and_deactivate_dependents(), test_calendar_duration_aliases_compare_by_period_and_canonical_unit(), test_every_schema_activation_rule_has_expected_positive_case() (+9 more)

### Community 3 - "validation.py"
Cohesion: 0.42
Nodes (8): _column_values(), _datetime(), _datetime_order_issue(), _issue(), _number(), _outside_range(), Any, _slot_value()

### Community 4 - "QuestionOutput"
Cohesion: 0.10
Nodes (70): asyncio, FakeLLMClient, QuestionOutput, build_question_input(), build_question_instructions(), _contains_phrase(), _context_value(), _contextual_example() (+62 more)

### Community 5 - "test_openai_adapter.py"
Cohesion: 0.13
Nodes (28): SimpleNamespace, InjectedClient, PersistentChatInjectedClient, PersistentInjectedClient, asyncio, _question_request(), RaisingConnectionResponses, RaisingResponses (+20 more)

### Community 6 - "FetchResult"
Cohesion: 0.09
Nodes (24): DatasetSourceAdapter, AcquisitionMode, FetchResult, LicenseAssessment, _candidate(), international_catalog_adapters(), LocalUploadAdapter, NASAPowerAdapter (+16 more)

### Community 7 - "DatasetCandidate"
Cohesion: 0.15
Nodes (19): DatasetRanker, _frequency_unit(), _geography_matches(), ranking_sort_key(), Fail-closed eligibility and deterministic source ranking., _tokens(), DatasetCandidate, DatasetSearchQuery (+11 more)

### Community 8 - "Forecasting Requirement Elicitation"
Cohesion: 0.13
Nodes (15): Architecture and decision documentation, Deploy the FYP web service on Render, Forecast Specification and Dataset Handoff, Forecasting Requirement Elicitation, Interactive CLI, Intermediate Interview Boundary, Pipeline, Privacy and Secrets (+7 more)

### Community 9 - "ImageFile.py"
Cohesion: 0.08
Nodes (25): # FIXME: the fill decoder is not implemented, # FIXME: jpeg tables are tile dependent; the prefix, _encode_tile(), _get_oserror(), BaseException, IO, NamedTuple, OSError (+17 more)

### Community 10 - "ImagePalette"
Cohesion: 0.12
Nodes (11): ImagePalette, negative(), Exception, IO, setter, random(), Given an rgb tuple, allocate palette entry. .. warning:: This method is…, Save palette to text file. .. warning:: This method is experimental. (+3 more)

### Community 12 - "cli.py"
Cohesion: 0.13
Nodes (27): callback, command, ElicitationEngine, SQLiteDialogueRepository, build_dataset_service(), build_engine(), _compose_trace_sinks(), confirm_dataset() (+19 more)

### Community 14 - "evaluate_elicitation.py"
Cohesion: 0.23
Nodes (15): build_scenarios(), _case(), main(), Any, validate_scenarios(), compute_metrics(), _divide(), evaluate() (+7 more)

### Community 15 - "http.py"
Cohesion: 0.18
Nodes (9): HTTPRedirectHandler, Request, Any, ValueError, SecureHttpClient, UnsafeDatasetUrlError, validate_public_https_url(), _ValidatedRedirectHandler (+1 more)

### Community 16 - "RegistryClient"
Cohesion: 0.12
Nodes (27): Protocol, RuntimeError, _clean_payload(), _is_local_host(), _normalize_base_url(), Any, RegistryTraceSink, The registry returned an invalid or non-successful API response. (+19 more)

### Community 17 - "registry_adapter.py"
Cohesion: 0.20
Nodes (14): DatasetPayloadValidationError, _json_point_count(), Any, ValueError, validate_dataset_payload(), QualityReport, _as_optional_string(), _canonical_registry_target() (+6 more)

### Community 18 - "FakeAdapter"
Cohesion: 0.41
Nodes (12): _candidate(), FakeAdapter, parametrize, Path, _service(), test_discovery_returns_only_top_three_and_isolates_adapter_failures(), test_executable_payload_fails_before_object_storage(), test_invalid_or_inadequate_dataset_payloads_fail_closed() (+4 more)

### Community 19 - "RegistryDatasetAdapter"
Cohesion: 0.22
Nodes (13): RegistryDatasetAdapter, ApprovedFutureSource, FakeHttp, FakeRegistryClient, Any, _source(), test_configured_registry_replaces_remote_catalog_adapters_but_keeps_local_uploads(), test_describe_returns_cached_candidate_by_stable_registry_slug() (+5 more)

### Community 21 - "Image.py"
Cohesion: 0.04
Nodes (46): RuntimeWarning, Format, IntEnum, A Pillow loader for .ftc and .ftu files (FTEX) Jerome Leclanche…, _decompression_bomb_check(), DecompressionBombError, DecompressionBombWarning, getmodebandnames() (+38 more)

### Community 34 - ".__init__"
Cohesion: 0.18
Nodes (6): BaseHTTPRequestHandler, HTTPStatus, ContentAddressedObjectStore, Path, DashboardServer, run_web_server()

### Community 35 - "web.py"
Cohesion: 0.16
Nodes (20): Connection, _connect(), dashboard_html(), _extract_uploaded_columns(), _json_default(), _list_table(), Any, DialogueState (+12 more)

### Community 36 - "query_from_specification"
Cohesion: 0.29
Nodes (10): _date(), _duration_text(), Any, ForecastingSpecification, query_from_specification(), _string_list(), _text_value(), test_query_from_specification_preserves_prompt_separately_from_registry_target() (+2 more)

### Community 37 - "DatasetVersion"
Cohesion: 0.08
Nodes (25): BaseModel, DatasetCandidateNotSelectableError, DatasetDiscoveryService, DatasetPlanNotFoundError, DatasetSelectionNotFoundError, KeyError, UUID, ValueError (+17 more)

### Community 39 - "TiffImagePlugin.py"
Cohesion: 0.06
Nodes (44): ModuleType, i16be(), deprecate(), Deprecations helper. :param deprecated: Name of thing to be deprecated. :param…, fromarray(), Creates an image memory from an object exporting the array interface (using the…, __getattr__(), Any (+36 more)

### Community 40 - "ForecastingSpecification"
Cohesion: 0.13
Nodes (11): ForecastingSpecification, DialogueRepository, Any, Protocol, UUID, Any, BaseModel, Connection (+3 more)

### Community 42 - "test_render_readiness.py"
Cohesion: 0.24
Nodes (10): Run the web interface; PORT is used automatically when provided by Render., web(), HealthyRegistryClient, _settings(), test_cli_dataset_service_passes_settings_to_adapter_factory(), test_healthz_reports_app_and_registry_status_without_secrets(), test_required_registry_failure_returns_service_unavailable(), test_web_dashboard_uses_registry_configured_adapters() (+2 more)

### Community 43 - "Image"
Cohesion: 0.03
Nodes (48): PrettyPrinter, IO, _save(), IO, _save(), IO, _save(), blend() (+40 more)

### Community 45 - "o8"
Cohesion: 0.09
Nodes (17): o8(), BmpRleDecoder, IO, _save(), PpmDecoder, _accept(), IO, QoiEncoder (+9 more)

### Community 46 - "ValueError"
Cohesion: 0.09
Nodes (11): model_validator, This operation will destroy the image core and release its memory. The image…, _compute_regular_polygon_vertices(), Generate a list of vertices for a 2D regular polygon. :param bounding_circle:…, Create a drawing instance. :param im: The image to draw in. :param mode:…, IO, _save(), PngStream (+3 more)

### Community 48 - "_Operand"
Cohesion: 0.06
Nodes (22): FontFile, puti16(), BinaryIO, Write network order (big-endian) 16-bit sequence, Base class for raster font file handlers., Create metrics and bitmap, eval(), imagemath_convert() (+14 more)

### Community 49 - "ImageCmsProfile"
Cohesion: 0.06
Nodes (47): CmsProfile, _CmsProfileCompatible, SupportsFloat, SupportsInt, applyTransform(), buildProofTransform(), buildTransform(), createProfile() (+39 more)

### Community 52 - ".load"
Cohesion: 0.05
Nodes (26): Dither, CapsuleType, Convert the image to 'P' mode with the specified number of colors. :param…, Copies this image. Use this method if you wish to paste things into an image,…, Filters this image using the given filter. For a list of available filters, see…, Returns a tuple containing the name of each band in this image. For example,…, Calculates the bounding box of the non-zero regions in the image. :param…, Returns a list of colors used in this image. The colors will be in the image's… (+18 more)

### Community 53 - "Any"
Cohesion: 0.07
Nodes (29): DisplayViewer, EogViewer, GmDisplayViewer, IPythonViewer, MacViewer, Any, Save to temporary file and return filename., Display the given image. (+21 more)

### Community 54 - "BmpImagePlugin.py"
Cohesion: 0.08
Nodes (26): i16le(), i32le(), o16le(), o32le(), Converts a 2-bytes (16 bits) string to an unsigned integer. :param c: string…, Converts a 4-bytes (32 bits) string to an unsigned integer. :param c: string…, _dib_accept(), _dib_save() (+18 more)

### Community 55 - "DeferredError"
Cohesion: 0.06
Nodes (28): _accept(), DcxImageFile, isImageType(), Checks if an object is an image object. .. warning:: This function is for…, align8to32(), Any, converts each scanline of data from 8 bit to 32 bit aligned, (Internal) Turns an RGB color into a Qt compatible color integer. (+20 more)

### Community 56 - "ImageOps.py"
Cohesion: 0.06
Nodes (44): Transpose, autocontrast(), _border(), _color(), colorize(), contain(), cover(), crop() (+36 more)

### Community 57 - "Any"
Cohesion: 0.07
Nodes (16): _ExifBase, ImagingEncoder, Exif, _getencoder(), Any, StrOrBytesPath, Returns a dictionary containing the XMP tags. Requires defusedxml to be…, Returns the image palette as a list. :param rawmode: The mode in which to… (+8 more)

### Community 58 - "Draw"
Cohesion: 0.10
Nodes (23): Brush, Draw, Font, Pen, Any, AnyStr, BinaryIO, Coords (+15 more)

### Community 59 - "ElicitationEngine"
Cohesion: 0.06
Nodes (63): DialogueRepository, QuestionRequest, SlotDefinition, _duration_from_text(), _duration_unit_from_text(), _enum_key(), extract_explicit_forecast_horizon(), extract_explicit_frequency() (+55 more)

### Community 60 - "_binary.py"
Cohesion: 0.08
Nodes (23): i32be(), i8(), Converts a 2-bytes (16 bits) string to a signed integer. :param c: string…, Converts a 2-bytes (16 bits) string to a signed integer, big endian. :param c:…, Converts a 4-bytes (32 bits) string to a signed integer. :param c: string…, Converts a 4-bytes (32 bits) string to a signed integer, big endian. :param c:…, si16be(), si16le() (+15 more)

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
Cohesion: 0.24
Nodes (13): BLUR, BuiltinFilter, CONTOUR, DETAIL, EDGE_ENHANCE, EDGE_ENHANCE_MORE, EMBOSS, FIND_EDGES (+5 more)

### Community 65 - "PhotoImage"
Cohesion: 0.07
Nodes (18): BitmapImage, _get_image_from_kw(), getimage(), PhotoImage, Any, CapsuleType, _pyimagingtkcall(), Get the Tkinter photo image identifier. This method is automatically called by… (+10 more)

### Community 66 - "BlpImagePlugin.py"
Cohesion: 0.10
Nodes (22): _accept(), AlphaEncoding, BLP1Decoder, BLP2Decoder, _BLPBaseDecoder, BLPEncoder, BLPFormatError, BlpImageFile (+14 more)

### Community 67 - "ImagePalette.py"
Cohesion: 0.09
Nodes (15): GimpGradientFile, GradientFile, linear(), IO, File handler for GIMP's gradient format., sine(), sphere_decreasing(), sphere_increasing() (+7 more)

### Community 68 - "build_report.py"
Cohesion: 0.19
Nodes (30): blocks(), change_once(), chapter(), conclusion(), design(), figure(), front_matter(), glossary() (+22 more)

### Community 69 - "ImageFileDirectory_v2"
Cohesion: 0.12
Nodes (8): _IFDv2Base, _LoaderFunc, _accept(), ImageFileDirectory_v2, This class represents a TIFF tag directory. To speed things up, we don't decode…, Initialize an ImageFileDirectory. To construct an ImageFileDirectory from a…, _register_basic(), _register_loader()

### Community 70 - "features.py"
Cohesion: 0.12
Nodes (27): check(), check_codec(), check_feature(), check_module(), get_supported(), get_supported_codecs(), get_supported_features(), get_supported_modules() (+19 more)

### Community 71 - "state_reducer.py"
Cohesion: 0.27
Nodes (11): Intent, _apply_update(), _canonical_evidence(), _check_contract(), DialogueState, ExtractorResult, ForecastingSchema, SlotUpdate (+3 more)

### Community 72 - "PngImageFile"
Cohesion: 0.08
Nodes (15): str, _accept(), iTXt, PngImageFile, PngInfo, Any, internal: finished reading image data, Subclass of string to allow iTXt chunks to look like strings while keeping… (+7 more)

### Community 73 - "ImageDraw"
Cohesion: 0.19
Nodes (12): _Ink, _Outline, Draw(), ImageDraw, Coords, Draw a circle given center coordinates and a radius., Draw a line, or a connected sequence of line segments., (Experimental) Draw a shape. (+4 more)

### Community 74 - "Decision records"
Cohesion: 0.07
Nodes (27): D-001 — Hybrid LLM plus deterministic pipeline, D-002 — Schema and SQLite state are authoritative, D-003 — Evidence-bound extraction, D-004 — Persistent provider context is a pilot, not the source of truth, D-005 — Intermediate useful brief, D-006 — Catalog facts are deferred until dataset selection, D-007 — Generated questions are bounded and have a deterministic fallback, D-008 — Explicit confirmation gates the handoff (+19 more)

### Community 75 - "PngImagePlugin.py"
Cohesion: 0.14
Nodes (19): o16be(), o32be(), Blend, _crc32(), Disposal, _fdat, _Frame, getchunks() (+11 more)

### Community 76 - "DialogueState"
Cohesion: 0.09
Nodes (28): AsyncOpenAI, Exception, MonkeyPatch, _duration_semantics(), _duration_unit(), _mentioned(), _multi_geography(), _same_granularity() (+20 more)

### Community 78 - "LutBuilder"
Cohesion: 0.09
Nodes (13): LutBuilder, MorphOp, string_permute takes a pattern and a permutation and returns the string…, pattern_permute takes a basic pattern and its result and clones the pattern…, Compile all patterns into a morphology lut. TBD :Build based on (file)…, A class for binary morphological operators, Create a binary morphological operator, Get a list of coordinates matching the morphological operation on an image.… (+5 more)

### Community 79 - "Jpeg2KImagePlugin.py"
Cohesion: 0.17
Nodes (11): Jpeg2KImageFile, _parse_codestream(), _parse_jp2_header(), IO, PixelAccess, setter, Parse the JPEG 2000 codestream to extract the size and component count from the…, Convert JPEG2000's (numerator, denominator, exponent-base-10) resolution,… (+3 more)

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
Cohesion: 0.08
Nodes (15): alpha_composite(), _apply_env_variables(), getmodebase(), ImagingCore, NumpyArray, setter, Returns a rectangular region from this image. The box is a 4-tuple defining the…, Returns a rectangular region from the core image object im. This is equivalent… (+7 more)

### Community 87 - "ImageFile"
Cohesion: 0.13
Nodes (9): fromqimage(), QImage, Creates an image instance from a QImage image, ImageFile, Any, Base class for image file format handlers., Closes the file pointer, if possible. This operation will destroy the image…, getiptcinfo() (+1 more)

### Community 88 - "ImageFont"
Cohesion: 0.16
Nodes (14): Any, AnyStr, Get the current default font. To set the default font for this ImageDraw…, Get the length of a given string, in pixels with 1/64 precision., Get the bounding box of a given string, in pixels., ImageFont, load(), load_path() (+6 more)

### Community 89 - "Any"
Cohesion: 0.12
Nodes (10): Any, ImagingCore, Create a bitmap for the text. If the font uses antialiasing, the bitmap should…, Returns bounding box (in pixels) of given text. .. versionadded:: 9.2.0 :param…, Returns length (in pixels) of given text. This is the amount by which following…, Returns length (in pixels with 1/64 precision) of given text when rendered in…, Returns bounding box (in pixels) of given text relative to given anchor when…, Create a bitmap for the text. If the font uses antialiasing, the bitmap should… (+2 more)

### Community 90 - "Stat"
Cohesion: 0.10
Nodes (11): Squared sum of all pixels for each band in the image., Average (arithmetic mean) pixel level for each band in the image., Median pixel level for each band in the image., RMS (root-mean-square) for each band in the image., Variance for each band in the image., Standard deviation for each band in the image., Calculate statistics for the given image. If a mask is included, only the…, Min/max values for each band in the image. .. note:: This relies on the… (+3 more)

### Community 91 - "DdsImagePlugin.py"
Cohesion: 0.20
Nodes (12): D3DFMT, DDPF, DDSCAPS, DDSCAPS2, DDSD, DdsRgbDecoder, DXGI_FORMAT, IntEnum (+4 more)

### Community 92 - "new"
Cohesion: 0.21
Nodes (12): _check_size(), frombuffer(), frombytes(), new(), Common check to enforce type and sanity check on size tuples :param size:…, Creates a new image with the given mode and size. :param mode: The mode to use…, Creates a copy of an image memory from pixel data in a buffer. In its simplest…, Creates an image memory referencing pixel data in a byte buffer. This function… (+4 more)

### Community 93 - ".__init__"
Cohesion: 0.22
Nodes (3): StrOrBytesPath, PyCodecState, Override to perform codec specific initialization :param args: Tuple of arg…

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
Cohesion: 0.21
Nodes (16): build_extractor_input(), _context_slot(), _is_secret_key(), Any, _redact_text(), safe_provider_value(), _stable_sort_key(), parametrize (+8 more)

### Community 104 - "Transform"
Cohesion: 0.13
Nodes (14): AffineTransform, ExtentTransform, MeshTransform, PerspectiveTransform, Any, QuadTransform, Define a quad image transform. Maps a quadrilateral (a region defined by four…, Define a mesh image transform. A mesh transform consists of one or more… (+6 more)

### Community 105 - "IndirectReference"
Cohesion: 0.18
Nodes (4): IndirectObjectDef, IndirectReference, IndirectReferenceTuple, NamedTuple

### Community 106 - "WebPImagePlugin.py"
Cohesion: 0.19
Nodes (7): _convert_frame(), Any, IO, PixelAccess, _save(), _save_all(), WebPImageFile

### Community 107 - "ImagingCore"
Cohesion: 0.25
Nodes (4): Filter, ModeFilter, ImagingCore, Create a mode filter. Picks the most frequent pixel value in a box with the…

### Community 108 - "ImagePointTransform"
Cohesion: 0.14
Nodes (6): _getscaleoffset(), ImagePointHandler, ImagePointTransform, Maps this image through a lookup table or function. :param lut: A lookup table,…, Used as a mixin by point transforms (for use with…, Used with :py:meth:`~PIL.Image.Image.point` for single band images with more…

### Community 109 - "_Enhance"
Cohesion: 0.13
Nodes (10): Brightness, Color, Contrast, _Enhance, Adjust image sharpness. This class can be used to adjust the sharpness of an…, Returns an enhanced image. :param factor: A floating point value controlling…, Adjust image color balance. This class can be used to adjust the colour balance…, Adjust image contrast. This class can be used to control the contrast of an… (+2 more)

### Community 110 - "ImageFileDirectory_v1"
Cohesion: 0.14
Nodes (6): _delegate(), ImageFileDirectory_v1, Any, This class represents the **legacy** interface to a TIFF tag directory. Exposes…, Returns an :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v2` instance with…, :returns: dict of name|key: value Returns the complete tag dictionary, with…

### Community 111 - "models.py"
Cohesion: 0.13
Nodes (16): _decode_candidate_value(), Any, BaseModel, ReadinessReport, SlotUpdate, TurnResult, FakeEngine, UUID (+8 more)

### Community 112 - "StubHandler"
Cohesion: 0.15
Nodes (11): _accept(), BufrStubImageFile, Install application-specific BUFR image handler. :param handler: Handler object., register_handler(), Install application-specific GRIB image handler. :param handler: Handler object., register_handler(), Install application-specific HDF5 image handler. :param handler: Handler object., register_handler() (+3 more)

### Community 113 - "ContainerIO"
Cohesion: 0.12
Nodes (8): ContainerIO, AnyStr, Read a line of text. :param n: Number of bytes to read. If omitted, zero or…, Read multiple lines of text. :param n: Number of lines to read. If omitted,…, A file object that provides read access to a part of an existing file (for…, Move file pointer. :param offset: Offset in bytes. :param mode: Starting…, Get current file pointer. :returns: Offset from start of region, in bytes., Read data. :param n: Number of bytes to read. If omitted, zero or negative,…

### Community 114 - "EpsImagePlugin.py"
Cohesion: 0.19
Nodes (10): EpsImageFile, Ghostscript(), has_ghostscript(), ImagingCore, IO, PixelAccess, EPS File Parser for the Python Imaging Library, EPS Writer for the Python Imaging Library. (+2 more)

### Community 115 - "PyEncoder"
Cohesion: 0.22
Nodes (7): Registers an image encoder. This function should not be used in application…, register_encoder(), PyEncoder, Python implementation of a format encoder. Override this class and add the…, Override to perform the encoding process. :param bufsize: Buffer size.…, If ``pushes_fd`` is ``True``, then this method will be used, and ``encode()``…, :param fh: File handle. :param bufsize: Buffer size. :returns: If finished…

### Community 116 - "RankFilter"
Cohesion: 0.15
Nodes (8): MaxFilter, MedianFilter, MinFilter, RankFilter, Create a median filter. Picks the median pixel value in a window with the given…, Create a min filter. Picks the lowest pixel value in a window with the given…, Create a max filter. Picks the largest pixel value in a window with the given…, Create a rank filter. The rank filter sorts all pixels in a window of the given…

### Community 117 - "ChunkStream"
Cohesion: 0.21
Nodes (4): ChunkStream, Fetch a new chunk. Returns header information., Call the appropriate chunk handler, Read and verify checksum

### Community 119 - ".load"
Cohesion: 0.22
Nodes (4): _T_co, PixelAccess, Load image data based on tile list, (Hook) Find actual image loader.

### Community 120 - "MultibandFilter"
Cohesion: 0.25
Nodes (5): BoxBlur, GaussianBlur, MultibandFilter, Blurs the image with a sequence of extended box filters, which approximates a…, Blurs the image by setting each pixel to the average value of the pixels in a…

### Community 121 - "IO"
Cohesion: 0.23
Nodes (5): IO, StrOrBytesPath, :param offset: Distance to seek. :param whence: Whether the distance is…, _save(), _save_all()

### Community 122 - "Color3DLUT"
Cohesion: 0.20
Nodes (6): Color3DLUT, Any, NumpyArray, Three-dimensional color lookup table. Transforms 3-channel pixels using the…, Generates new LUT using provided callback. :param size: Size of the table.…, Transforms the table values using provided callback and returns a new LUT with…

### Community 123 - "PyDecoder"
Cohesion: 0.13
Nodes (10): Registers an image decoder. This function should not be used in application…, register_decoder(), ImagingCore, PyCodec, PyDecoder, Override to perform codec specific cleanup :returns: None, Called from ImageFile to set the core output image for the codec :param im: A…, Python implementation of a format decoder. Override this class and add the… (+2 more)

### Community 124 - "config.py"
Cohesion: 0.23
Nodes (16): BaseSettings, DatasetDiscoveryService, _answer_for_slot(), _build_dataset_service(), _build_engine(), _load_scenarios(), main(), Any (+8 more)

### Community 125 - "_i"
Cohesion: 0.39
Nodes (4): _i(), IptcImageFile, PixelAccess, .. deprecated:: 10.2.0

### Community 126 - "JsonlPipelineLogger"
Cohesion: 0.20
Nodes (6): Durable, redacted observability helpers for the elicitation pipeline., JsonlPipelineLogger, Any, Path, Append one redacted, machine-readable record for every pipeline trace event., test_pipeline_logger_writes_timestamped_redacted_jsonl()

### Community 128 - "._bitmap"
Cohesion: 0.22
Nodes (7): _accept(), BmpImageFile, DibImageFile, Open file, check magic number and read header, Image plugin for the Windows Bitmap format (BMP), Read relevant info about the BMP, Seeks to the given frame in this sequence file. If you seek beyond the end of…

### Community 131 - "Project Decisions"
Cohesion: 0.20
Nodes (7): 2026-11-22 — Deliverable III author-voice edition, D-027 — Final Deliverable III source package, Decision index, Future decision record template, How to maintain this file, Project Decisions, Runtime “why” checklist

### Community 132 - "Review Focus"
Cohesion: 0.20
Nodes (9): Deterministic Interview Pilot Implementation Plan, Global Constraints, Review Focus, Task 1: Capture the baseline, Task 2: Make pending-slot answers authoritative, Task 3: Protect forecast intent and catalog source selection, Task 4: Sanitize confirmed values before registry queries, Task 4b: Recover explicit initial time cues (+1 more)

### Community 133 - "fromqimage"
Cohesion: 0.67
Nodes (4): fromqimage(), fromqpixmap(), QPixmap, :param im: QImage or PIL ImageQt object

### Community 134 - "FakeHttp"
Cohesion: 0.31
Nodes (6): FakeHttp, Any, test_ndma_mhvra_and_open_data_pakistan_are_not_automatic_sources(), test_pmd_wis2_core_metadata_is_production_eligible_input(), test_research_catalog_stays_separate(), test_who_adapter_returns_concrete_matching_indicator_endpoint()

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
Cohesion: 0.15
Nodes (8): NotImplementedError, NoReturn, _accept(), DdsImageFile, :param axes: A list of values for each axis. :exception OSError: If the font is…, grabclipboard(), make_linear_lut(), sepia()

### Community 142 - "ImageQt"
Cohesion: 0.28
Nodes (7): QByteArray, Returns a QImage copy of this image, ImageQt, QImage, An PIL image wrapper for Qt. This is a subclass of PyQt's QImage class. :param…, toqimage(), toqpixmap()

### Community 143 - "ContainerIO.py"
Cohesion: 0.22
Nodes (5): IO, Create file object. :param file: Existing file. :param offset: Start of region,…, A file object that provides read access to a given member of a TAR file., Create file object. :param tarfile: Name of TAR file. :param file: Name of…, TarIO

### Community 144 - "MpoImagePlugin.py"
Cohesion: 0.21
Nodes (5): MpoImageFile, Any, IO, _save(), _save_all()

### Community 145 - "SupportsArrayInterface"
Cohesion: 0.18
Nodes (6): FitsGzipDecoder, An object that has an ``__array_interface__`` dictionary., SupportsArrayInterface, MspDecoder, QoiDecoder, SGI16Decoder

### Community 146 - "render_complete_workflow.mjs"
Cohesion: 0.25
Nodes (7): errors, logs, output, sampleTimes, transcript, webm, work

### Community 147 - ".frombytes"
Cohesion: 0.22
Nodes (8): ImagingDecoder, bdf_char(), BdfFontFile, BinaryIO, Font file plugin for the X11 BDF format., _getdecoder(), Loads this image with pixel data from a bytes object. This method is similar to…, grab()

### Community 149 - "GimpPaletteFile"
Cohesion: 0.39
Nodes (3): GimpPaletteFile, IO, File handler for GIMP's palette format.

### Community 150 - "IcoFile"
Cohesion: 0.11
Nodes (12): _accept(), IcoFile, IcoImageFile, IconHeader, NamedTuple, PixelAccess, setter, Parse image from file-like object containing ico file data (+4 more)

### Community 154 - "open"
Cohesion: 0.25
Nodes (6): open(), IO, PixelAccess, StrOrBytesPath, Load texture from a Quake2 WAL texture file. By default, a Quake2 standard…, WalImageFile

### Community 155 - "Global Constraints"
Cohesion: 0.29
Nodes (6): Forecasting Dialogue Hardening Implementation Plan, Global Constraints, Task 1: Regression Tests for Pending Answers and Source Ordering, Task 2: Deterministic Recovery and Dataset-Aware Validation, Task 3: Traceability and Novice-Friendly Questions, Task 4: Verification

### Community 156 - "Global Constraints"
Cohesion: 0.29
Nodes (6): Global Constraints, Intermediate Interview Boundary Implementation Plan, Task 1: Regression tests for priority context and bounded readiness, Task 2: Implement the intermediate policy, Task 3: Confirmation and documentation, Task 4: Verification

### Community 158 - "GdImageFile.py"
Cohesion: 0.08
Nodes (24): GdImageFile, open(), IO, StrOrBytesPath, Image plugin for the GD uncompressed format. Note that this format is not…, Load texture from a GD image file. :param fp: GD file name, or an opened file…, init(), open() (+16 more)

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

### Community 165 - "PdfImagePlugin.py"
Cohesion: 0.60
Nodes (5): IO, # FIXME: Should replace ASCIIHexDecode with RunLengthDecode, _save(), _save_all(), _write_image()

### Community 166 - "_TagInfo"
Cohesion: 0.40
Nodes (4): lookup(), NamedTuple, :param tag: Integer tag number :param group: Which…, _TagInfo

### Community 168 - "F26-012 Native LaTeX Report Conversion"
Cohesion: 0.40
Nodes (4): Constraints, F26-012 Native LaTeX Report Conversion, Goal, Work plan

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

### Community 188 - "Extraction and state transition"
Cohesion: 0.67
Nodes (3): 4. Provider extraction, 5. Apply or recover the extraction, Extraction and state transition

## Knowledge Gaps
- **156 isolated node(s):** `How to maintain this file`, `Decision index`, `D-001 — Hybrid LLM plus deterministic pipeline`, `D-002 — Schema and SQLite state are authoritative`, `D-003 — Evidence-bound extraction` (+151 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **60 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Image` connect `Image` to `._bitmap`, `Parser`, `ImageFile.py`, `StubImageFile`, `ImagePalette`, `PcfFontFile`, `NotImplementedError`, `ImageQt`, `MpoImagePlugin.py`, `.frombytes`, `Image.py`, `IcoFile`, `GdImageFile.py`, `PdfImagePlugin.py`, `TiffImagePlugin.py`, `fromarrow`, `fromqpixmap`, `ValueError`, `o8`, `_Operand`, `ImageCmsProfile`, `.load`, `Any`, `BmpImagePlugin.py`, `DeferredError`, `ImageOps.py`, `Any`, `Draw`, `ImageChops.py`, `Window`, `GifImagePlugin.py`, `PhotoImage`, `BlpImagePlugin.py`, `ImageDraw`, `PngImagePlugin.py`, `LutBuilder`, `Jpeg2KImagePlugin.py`, `.transform`, `AvifImagePlugin.py`, `.crop`, `ImageFile`, `ImageFont`, `Stat`, `DdsImagePlugin.py`, `new`, `.__init__`, `IcnsImagePlugin.py`, `PSDraw`, `Transform`, `WebPImagePlugin.py`, `ImagePointTransform`, `_Enhance`, `EpsImagePlugin.py`, `IO`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `load_schema()` connect `load_schema` to `SlotState`, `.__init__`, `is_slot_active`, `QuestionOutput`, `test_openai_adapter.py`, `build_extractor_input`, `cli.py`, `DialogueState`, `ValueError`, `evaluate_elicitation.py`, `ElicitationEngine`, `config.py`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `FreeTypeFont` connect `FreeTypeFont` to `NotImplementedError`, `Image.py`, `DeferredError`, `ImageFont`, `Any`, `.get_variation_axes`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 124 inferred relationships involving `ValueError` (e.g. with `_load_scenarios()` and `query_from_specification()`) actually correct?**
  _`ValueError` has 124 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `load_schema()` (e.g. with `main()` and `evaluate()`) actually correct?**
  _`load_schema()` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `DatasetCandidate` (e.g. with `DatasetDiscoveryService` and `DatasetRanker`) actually correct?**
  _`DatasetCandidate` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 67 inferred relationships involving `create_initial_state()` (e.g. with `.start_dialogue()` and `seed_world_bank_demo()`) actually correct?**
  _`create_initial_state()` has 67 INFERRED edges - model-reasoned connections that need verification._