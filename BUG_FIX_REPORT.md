# Bug Identification & Fix Report

**Project:** Technocart Business Machines assessment  
**Date:** 2026-10-12

## Scope and History

This report describes defects addressed by the current implementations and the tests that cover them. The available Git history does not contain an earlier version of the application code: the prior commit contains only a placeholder, and the current commit adds the applications and tests together. Therefore, exact before-and-after source changes cannot be independently reconstructed from Git.

## Bugs Identified and Fixes

### 1. Book updates could persist the wrong year or price

- **Root cause:** Update values pass through the HTTP controller and service before reaching SQL. A mismatch in the positional argument order can assign the year to the price field or vice versa.
- **Fix:** The controller and service pass values in a consistent order, then build a named object with `published_year` and `price` before the repository update.
- **Files:** `nodejs/src/controllers/bookController.js`, `nodejs/src/services/bookService.js`, `nodejs/src/repositories/bookRepository.js`.
- **Verification:** `updates a book without swapping year and price` in `nodejs/tests/books.test.js`.

### 2. Catalog search did not reliably filter the main book list

- **Root cause:** Search terms supplied as the `q` query parameter must be carried through the list endpoint and included in the database query.
- **Fix:** The controller forwards `q`; the repository applies a parameterized search across title, author, and ISBN. The dedicated search route uses the same repository behavior.
- **Files:** `nodejs/src/controllers/bookController.js`, `nodejs/src/repositories/bookRepository.js`, `nodejs/src/services/bookService.js`.
- **Verification:** `finds books from the search box query` and `searches using the dedicated search route` in `nodejs/tests/books.test.js`.

### 3. Stock adjustments could request invalid quantities

- **Root cause:** Unvalidated adjustment values or decrements larger than available stock could result in invalid inventory state.
- **Fix:** Adjustments must be non-zero integers, and the service rejects any update that would make quantity negative with an `Insufficient stock` response.
- **Files:** `nodejs/src/middleware/validate.js`, `nodejs/src/services/stockService.js`, `nodejs/src/controllers/bookController.js`.
- **Verification:** Stock increase, decrease, and below-zero rejection tests in `nodejs/tests/books.test.js`.

### 4. Invalid or duplicate book data could reach persistence without useful client errors

- **Root cause:** Missing or malformed fields and duplicate ISBN values need validation and explicit handling at the API and database boundaries.
- **Fix:** Required fields, year, price, quantity, ISBN format, and IDs are validated; unique ISBN constraint errors are translated to HTTP 409 instead of an unhandled database error.
- **Files:** `nodejs/src/middleware/validate.js`, `nodejs/src/services/bookService.js`, `nodejs/src/repositories/bookRepository.js`, `nodejs/src/middleware/errorHandler.js`.
- **Verification:** Missing-title and duplicate-ISBN rejection tests in `nodejs/tests/books.test.js`; the suite also tests CRUD and not-found responses.

### 5. OCR could receive the wrong image representation

- **Root cause:** OCR accuracy depends on passing the preprocessed image through the recognition pipeline, rather than sending an unprocessed or color image.
- **Fix:** The pipeline decodes, resizes, preprocesses, and passes the prepared image into OCR.
- **Files:** `python/app/preprocessing/image_ops.py`, `python/app/recognition/ocr.py`, `python/app/services/pipeline.py`.
- **Verification:** `test_pipeline_sends_preprocessed_image_to_ocr` in `python/tests/test_recognize.py`.

### 6. Resizing could distort uploaded handwriting

- **Root cause:** Resizing to fixed dimensions without a shared scale factor changes the image's aspect ratio.
- **Fix:** The resize operation fits images within the configured maximum width and height while preserving their aspect ratio.
- **Files:** `python/app/preprocessing/image_ops.py`.
- **Verification:** `test_resize_image_preserves_aspect_ratio` in `python/tests/test_recognize.py`.

### 7. Unsafe or invalid uploads and result IDs could reach file operations

- **Root cause:** User-supplied filenames, MIME types, and file contents are not trustworthy path or format indicators; result IDs must also be constrained before constructing storage paths.
- **Fix:** Uploads are restricted by filename, extension, MIME type, image signature, and 5 MB size limit. Result IDs are generated as UUID hex strings and validated before result-file access.
- **Files:** `python/app/utils/validation.py`, `python/app/utils/files.py`, `python/app/routes/recognize.py`.
- **Verification:** Upload rejection and result-download tests in `python/tests/test_recognize.py`.

## Testing and Verification

- **Node.js:** `npm test` in `nodejs/` passed: 1 suite, 17 tests.
- **Python:** `py -3.11 -m pytest` could not run because `pytest` is not installed in the available Python 3.11 environment. The Python 3.14 environment also lacks `pytest`. Python tests therefore remain unverified in this environment.
- Python OCR tests mock Tesseract; they verify request handling and pipeline wiring, not recognition accuracy against a real Tesseract installation.

## Unresolved Issues

- OCR is configured with Tesseract page segmentation mode 7, which assumes a single text line. The supplied tall/multi-line samples may need a different segmentation mode or line-by-line processing; real OCR output has not been verified here.
- Run `python -m pip install -r requirements.txt` from `python/`, then `python -m pytest`, and validate the sample images with Tesseract installed to complete Python verification.
- Because an earlier source revision is not present in Git history, the file lists above identify the current implementation and relevant tests, not a verifiable historical diff of each fix.