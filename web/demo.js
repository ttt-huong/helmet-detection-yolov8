(() => {
  const WORN_CLASSES = new Set([
    'hard_hat_worn',
  ]);
  const CLASS_LABELS = {
    hard_hat_worn: 'Mũ bảo hộ công trường',
    depiction_region: 'Poster / ảnh / màn hình',
  };
  const EXPECTED_CLASS_NAMES = [
    'hard_hat_worn', 'depiction_region',
  ];
  const CLASS_COLORS = {
    hard_hat_worn: '#25845b',
    depiction_region: '#ba6659',
  };
  const IMAGE_MIMES_BY_EXTENSION = {
    jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp',
  };
  const ALLOWED_IMAGE_MIMES = new Set(Object.values(IMAGE_MIMES_BY_EXTENSION));
  const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
  const MAX_IMAGE_PIXELS = 24_000_000;
  const LIVE_PROBE_TIMEOUT_MS = 10_000;
  const HEALTH_PROBE_TIMEOUT_MS = 180_000;
  const INFERENCE_TIMEOUT_MS = 120_000;
  const MIN_INFERENCE_CONFIDENCE = 0.001;
  const elements = {
    apiStatus: document.querySelector('#api-status'),
    apiStatusText: document.querySelector('#api-status-text'),
    apiProcessState: document.querySelector('#api-process-state'),
    candidateCount: document.querySelector('#candidate-count'),
    confidenceInput: document.querySelector('#confidence-input'),
    confidenceValue: document.querySelector('#confidence-value'),
    confirmedCount: document.querySelector('#confirmed-count'),
    detectionList: document.querySelector('#detection-list'),
    demoNotice: document.querySelector('.demo-notice'),
    dropZone: document.querySelector('#drop-zone'),
    fileDetails: document.querySelector('#file-details'),
    fileInput: document.querySelector('#image-input'),
    fileName: document.querySelector('#file-name'),
    fileSummary: document.querySelector('#file-summary'),
    imageCanvas: document.querySelector('#preview-canvas'),
    imageTransferDetail: document.querySelector('#image-transfer-detail'),
    imageTransferTitle: document.querySelector('#image-transfer-title'),
    inferenceReadinessState: document.querySelector('#inference-readiness-state'),
    previewEmpty: document.querySelector('#preview-empty'),
    previewFrame: document.querySelector('#preview-frame'),
    recheckApiButton: document.querySelector('#recheck-api'),
    removeFile: document.querySelector('#remove-file'),
    requestError: document.querySelector('#request-error'),
    requestStatus: document.querySelector('#request-status'),
    resultBadge: document.querySelector('#result-badge'),
    resultSummary: document.querySelector('#result-summary'),
    runButton: document.querySelector('#run-inference'),
    runLabel: document.querySelector('#run-label'),
    suppressedCount: document.querySelector('#suppressed-count'),
  };
  const canvasContext = elements.imageCanvas.getContext('2d');
  let selectedFile = null;
  let previewImage = null;
  let previewUrl = null;
  let activeRequest = null;
  let checkingApi = false;
  let pendingApiCheck = false;
  let apiReady = false;
  let fileSelectionToken = 0;

  function setReadinessStatus(processState, inferenceState) {
    const labels = {
      checking: 'Đang kiểm tra',
      alive: 'Đang chạy',
      unreachable: 'Không kết nối',
      unknown: 'Chưa xác minh',
      ready: 'Sẵn sàng',
      blocked: 'Chưa sẵn sàng',
      unavailable: 'Chưa khả dụng',
    };
    elements.apiProcessState.dataset.state = processState;
    elements.apiProcessState.textContent = labels[processState] ?? labels.unknown;
    elements.inferenceReadinessState.dataset.state = inferenceState;
    elements.inferenceReadinessState.textContent = labels[inferenceState] ?? labels.unknown;
  }

  function setApiStatus(state, message, detail = '', readiness = null) {
    apiReady = state === 'ready';
    elements.apiStatus.dataset.state = state;
    elements.apiStatusText.textContent = message;
    elements.demoNotice.dataset.state = state;
    const defaultReadiness = {
      checking: ['checking', 'checking'],
      ready: ['alive', 'ready'],
      'preview-only': ['unknown', 'unavailable'],
      'model-unavailable': ['alive', 'blocked'],
      offline: ['unreachable', 'unavailable'],
    }[state] ?? ['unknown', 'unavailable'];
    setReadinessStatus(...(readiness ?? defaultReadiness));
    const transferNotice = {
      ready: ['Sẵn sàng suy luận.', 'Ảnh chỉ được gửi đến máy chủ khi bạn bấm Chạy kiểm tra. Kết quả là ứng viên cần rà toàn cảnh; số người đội mũ được xác nhận luôn là 0.'],
      checking: ['Đang kiểm tra API.', 'Ảnh vẫn ở trong trình duyệt và chưa được gửi.'],
      'preview-only': ['Chỉ đang xem trước tĩnh.', detail || 'Trang này chưa cùng origin với inference API. Hãy mở demo từ origin đang phục vụ API. Ảnh chưa được gửi.'],
      'model-unavailable': ['API có phản hồi · inference chưa sẵn sàng.', detail || 'Health chưa xác nhận model_loaded và thứ tự lớp mong đợi. Ảnh chưa được gửi.'],
      offline: ['Không kết nối được inference API.', detail || 'Ảnh vẫn ở trong trình duyệt và chưa được gửi.']
    }[state];
    elements.imageTransferTitle.textContent = transferNotice[0];
    elements.imageTransferDetail.textContent = transferNotice[1];
    if (!activeRequest) {
      elements.runButton.disabled = !selectedFile || !apiReady;
      syncPreviewApiStatus();
    }
  }

  function syncPreviewApiStatus() {
    if (!selectedFile || !elements.resultSummary.hidden || elements.resultBadge.dataset.state === 'error') return;
    if (elements.apiStatus.dataset.state === 'checking') {
      elements.requestStatus.textContent = 'Đang kiểm tra API. Ảnh vẫn ở trong trình duyệt và chưa được gửi.';
      elements.resultBadge.textContent = 'Đang kiểm tra API';
    } else if (apiReady) {
      elements.requestStatus.textContent = 'Ảnh được giữ trong trình duyệt cho đến khi bạn chạy kiểm tra.';
      elements.resultBadge.textContent = 'Sẵn sàng';
    } else if (elements.apiStatus.dataset.state === 'preview-only') {
      elements.requestStatus.textContent = 'Đang xem trước tĩnh; origin này không có inference API. Ảnh vẫn ở trong trình duyệt và chưa được gửi.';
      elements.resultBadge.textContent = 'Chỉ xem trước';
    } else if (elements.apiStatus.dataset.state === 'model-unavailable') {
      elements.requestStatus.textContent = 'API có phản hồi nhưng inference chưa sẵn sàng. Ảnh vẫn ở trong trình duyệt và chưa được gửi.';
      elements.resultBadge.textContent = 'Inference chưa sẵn sàng';
    } else {
      elements.requestStatus.textContent = 'Không kết nối được API. Ảnh vẫn ở trong trình duyệt và chưa được gửi.';
      elements.resultBadge.textContent = 'API chưa kết nối';
    }
  }

  function hasExpectedClassOrder(value) {
    let names;
    if (Array.isArray(value)) {
      names = value;
    } else if (value && typeof value === 'object') {
      const keys = Object.keys(value).sort((first, second) => Number(first) - Number(second));
      if (keys.length !== EXPECTED_CLASS_NAMES.length
        || keys.some((key, index) => key !== String(index))) return false;
      names = keys.map((key) => value[key]);
    } else {
      return false;
    }
    return names.length === EXPECTED_CLASS_NAMES.length
      && names.every((name, index) => name === EXPECTED_CLASS_NAMES[index]);
  }

  function modelUnavailableMessage(errorCode) {
    if (errorCode === 'model_path_not_configured') return 'Máy chủ chưa cấu hình MODEL_PATH.';
    if (errorCode === 'checkpoint_missing') return 'Chưa tìm thấy checkpoint trên máy chủ.';
    if (errorCode === 'checkpoint_incompatible') return 'Checkpoint không đúng model hardhat-only hai lớp hoặc thứ tự lớp.';
    if (errorCode === 'checkpoint_load_failed') return 'Không nạp được checkpoint hoặc dependency inference.';
    if (errorCode === 'release_manifest_missing') return 'Thiếu biên nhận khai báo các cổng poster/ảnh/màn hình đạt để triển khai checkpoint.';
    if (errorCode === 'release_manifest_invalid') return 'Biên nhận triển khai checkpoint không hợp lệ.';
    if (errorCode === 'release_gate_not_passed') return 'Biên nhận không khai báo các cổng poster/ảnh/màn hình đạt với metadata đã rà.';
    if (errorCode === 'release_checkpoint_hash_mismatch') return 'Checkpoint không khớp SHA-256 ghi trong biên nhận triển khai.';
    if (errorCode === 'release_test_summary_missing') return 'Thiếu báo cáo test khóa đi kèm biên nhận triển khai.';
    if (errorCode === 'release_test_summary_invalid') return 'Báo cáo test khóa không đọc được hoặc sai định dạng.';
    if (errorCode === 'release_test_summary_hash_mismatch') return 'Báo cáo test khóa không khớp biên nhận triển khai.';
    if (errorCode === 'release_test_summary_gate_mismatch') return 'Báo cáo test không khớp checkpoint/dữ liệu hoặc thiếu độ phủ poster/ảnh/màn hình.';
    if (errorCode === 'release_data_sufficiency_gate_mismatch') return 'Báo cáo phát hành thiếu số liệu bắt buộc hoặc chưa đạt số lượng hộp nhãn và nhóm nguồn tối thiểu.';
    if (errorCode === 'release_runtime_mismatch') return 'Runtime inference không khớp phiên bản Torch/CUDA đã ghi trong báo cáo train Colab.';
    if (errorCode === 'inference_gpu_unavailable') return 'API host chưa xác minh được GPU CUDA. Hãy kiểm tra GPU khả dụng và quyền truy cập GPU của dịch vụ API theo hướng dẫn triển khai.';
    return 'Inference API chưa sẵn sàng.';
  }

  function clearResults(status = 'Chọn ảnh rồi chạy kiểm tra.') {
    elements.resultSummary.hidden = true;
    elements.requestError.hidden = true;
    elements.requestError.textContent = '';
    elements.requestStatus.textContent = status;
    elements.resultBadge.textContent = 'Chưa chạy';
    elements.resultBadge.dataset.state = '';
    elements.detectionList.replaceChildren();
    if (previewImage) drawPreview([]);
  }

  async function checkApi() {
    if (checkingApi) {
      pendingApiCheck = true;
      return;
    }
    checkingApi = true;
    elements.recheckApiButton.disabled = true;
    elements.recheckApiButton.textContent = 'Đang kiểm tra…';
    setApiStatus('checking', 'Đang kiểm tra API');
    try {
      const readProbe = async (path, timeoutMs) => {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
        try {
          const response = await fetch(path, {
            cache: 'no-store',
            headers: { Accept: 'application/json' },
            signal: controller.signal,
          });
          const isJson = response.headers.get('content-type')?.includes('application/json') === true;
          const payload = isJson ? await response.json().catch(() => null) : null;
          return { response, isJson, payload, timedOut: false };
        } catch (error) {
          return { response: null, isJson: false, payload: null, timedOut: error?.name === 'AbortError' };
        } finally {
          window.clearTimeout(timeoutId);
        }
      };
      const [liveProbe, healthProbe] = await Promise.all([
        readProbe('/livez', LIVE_PROBE_TIMEOUT_MS),
        readProbe('/health', HEALTH_PROBE_TIMEOUT_MS),
      ]);
      const livezConfirmed = liveProbe?.response?.ok === true && liveProbe.payload?.status === 'alive';
      const healthRespondedAsApi = healthProbe?.isJson === true;
      const processAlive = livezConfirmed || healthRespondedAsApi;
      const probeResponded = Boolean(liveProbe?.response || healthProbe?.response);
      const processState = processAlive ? 'alive' : (probeResponded ? 'unknown' : 'unreachable');

      if (!healthProbe?.response) {
        const healthDetail = healthProbe?.timedOut
          ? 'GET /health vượt quá 180 giây; model có thể vẫn đang nạp. Hãy bấm “Kiểm tra lại” sau khi kiểm tra log API.'
          : 'GET /health không trả lời. Hãy kiểm tra API rồi bấm “Kiểm tra lại”.';
        if (livezConfirmed) {
          setApiStatus('model-unavailable', 'API đang chạy · chưa đọc được trạng thái model', `${healthDetail} Ảnh chưa được gửi.`, ['alive', 'blocked']);
        } else {
          const detail = probeResponded
            ? healthDetail
            : `${healthProbe?.timedOut || liveProbe?.timedOut ? 'Kiểm tra API đã hết thời gian chờ.' : 'Không xác minh được /livez hoặc /health.'} Ảnh vẫn ở trong trình duyệt và chưa được gửi.`;
          setApiStatus('offline', 'Không xác minh được inference API', detail, [processState, 'unavailable']);
        }
        return;
      }

      const { response, isJson, payload } = healthProbe;
      if (isJson && response.status === 200 && payload?.status === 'ready'
        && payload.model_loaded === true && hasExpectedClassOrder(payload.class_names)) {
        setApiStatus('ready', 'API xác nhận mô hình đã sẵn sàng', '', ['alive', 'ready']);
      } else if (isJson && (response.status === 503 || payload?.status === 'model_not_loaded')) {
        const reason = modelUnavailableMessage(payload?.error_code);
        setApiStatus('model-unavailable', 'API đang chạy · mô hình chưa sẵn sàng', reason, ['alive', 'blocked']);
      } else if (!isJson) {
        const detail = livezConfirmed
          ? 'Tiến trình web còn chạy nhưng /health không phải JSON của inference API. Hãy mở demo cùng origin với API. Ảnh chưa được gửi.'
          : 'Trang này chưa cùng origin với inference API. Hãy mở demo từ origin đang phục vụ API. Ảnh chưa được gửi.';
        setApiStatus('preview-only', 'Chưa có inference API tại origin này', detail, [processState, 'unavailable']);
      } else if (payload?.model_loaded === true) {
        const reason = hasExpectedClassOrder(payload.class_names)
          ? 'Health chưa xác nhận HTTP 200 cùng status="ready".'
          : 'Thứ tự lớp mô hình không khớp cấu hình yêu cầu.';
        setApiStatus('model-unavailable', 'API đang chạy · mô hình chưa sẵn sàng', reason, ['alive', 'blocked']);
      } else if (payload?.model_loaded === false) {
        setApiStatus('model-unavailable', 'API đang chạy · mô hình chưa sẵn sàng', 'Health chưa xác nhận model_loaded=true. Ảnh chưa được gửi.', ['alive', 'blocked']);
      } else {
        setApiStatus('model-unavailable', 'API đang chạy · trạng thái suy luận chưa xác minh', `Health trả HTTP ${response.status}; ảnh chưa được gửi.`, [processAlive ? 'alive' : processState, 'blocked']);
      }
    } finally {
      checkingApi = false;
      elements.recheckApiButton.disabled = false;
      elements.recheckApiButton.textContent = 'Kiểm tra lại';
      if (pendingApiCheck) {
        pendingApiCheck = false;
        checkApi();
      }
    }
  }

  function setFileError(message) {
    elements.previewEmpty.hidden = false;
    elements.previewFrame.hidden = true;
    elements.resultSummary.hidden = true;
    elements.requestError.textContent = message;
    elements.requestError.hidden = false;
    elements.requestStatus.textContent = 'Không thể dùng ảnh này.';
    elements.resultBadge.textContent = 'Ảnh không hợp lệ';
    elements.resultBadge.dataset.state = 'error';
    elements.runButton.disabled = true;
  }

  function resetSelectedFile() {
    fileSelectionToken += 1;
    activeRequest?.abort();
    activeRequest = null;
    selectedFile = null;
    previewImage = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    elements.fileInput.value = '';
    elements.fileSummary.hidden = true;
    elements.previewFrame.hidden = true;
    elements.previewEmpty.hidden = false;
    elements.runButton.disabled = true;
    clearResults();
    canvasContext.clearRect(0, 0, elements.imageCanvas.width, elements.imageCanvas.height);
  }

  function loadSelectedFile(file) {
    if (!file) return;
    const selectionToken = ++fileSelectionToken;
    activeRequest?.abort();
    activeRequest = null;
    selectedFile = null;
    previewImage = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    elements.previewFrame.hidden = true;
    elements.previewEmpty.hidden = true;
    elements.runButton.disabled = true;
    elements.fileName.textContent = file.name;
    elements.fileDetails.textContent = 'Đang đọc ảnh xem trước…';
    elements.fileSummary.hidden = false;
    clearResults('Đang đọc ảnh xem trước…');
    elements.resultBadge.textContent = 'Đang tải ảnh';

    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
    const uploadMimeType = ALLOWED_IMAGE_MIMES.has(file.type)
      ? file.type : IMAGE_MIMES_BY_EXTENSION[extension];
    if (!uploadMimeType) {
      resetSelectedFile();
      setFileError('Chỉ nhận ảnh JPG, PNG hoặc WEBP.');
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      resetSelectedFile();
      setFileError('Ảnh vượt giới hạn 10 MB. Hãy chọn ảnh nhỏ hơn.');
      return;
    }
    selectedFile = file;
    previewUrl = URL.createObjectURL(file);
    const selectedUrl = previewUrl;
    const image = new Image();
    image.onload = () => {
      if (selectionToken !== fileSelectionToken || selectedFile !== file || previewUrl !== selectedUrl) return;
      if (image.naturalWidth * image.naturalHeight > MAX_IMAGE_PIXELS) {
        resetSelectedFile();
        setFileError('Kích thước ảnh vượt giới hạn 24 megapixel.');
        return;
      }
      previewImage = image;
      elements.fileName.textContent = file.name;
      elements.fileDetails.textContent = `${image.naturalWidth} × ${image.naturalHeight}px · ${(file.size / (1024 * 1024)).toFixed(2)} MB`;
      elements.fileSummary.hidden = false;
      elements.previewEmpty.hidden = true;
      elements.previewFrame.hidden = false;
      elements.runButton.disabled = !apiReady;
      elements.requestError.hidden = true;
      elements.resultBadge.dataset.state = '';
      elements.resultSummary.hidden = true;
      syncPreviewApiStatus();
      drawPreview([]);
    };
    image.onerror = () => {
      if (selectionToken !== fileSelectionToken || selectedFile !== file || previewUrl !== selectedUrl) return;
      resetSelectedFile();
      setFileError('Không đọc được ảnh. Hãy chọn tệp ảnh hợp lệ.');
    };
    image.src = selectedUrl;
  }

  function boxStyle(item, suppressed = false) {
    if (suppressed) return { color: '#7a817b', dash: [8, 5] };
    if (item.source_status === 'uncertain_partial_depiction_overlap') {
      return { color: '#d09a35', dash: [5, 4] };
    }
    return { color: CLASS_COLORS[item.class_name] ?? '#657067', dash: [] };
  }

  function drawBox(item, suppressed = false) {
    const [x1, y1, x2, y2] = item.box_xyxy;
    const width = x2 - x1;
    const height = y2 - y1;
    if (!(width > 0 && height > 0)) return;
    const style = boxStyle(item, suppressed);
    const label = CLASS_LABELS[item.class_name] ?? item.class_name;
    const flag = suppressed ? ' · ĐÃ LOẠI' : WORN_CLASSES.has(item.class_name) ? ' · CHƯA TÍNH' : '';
    const text = `${label}${flag} ${Math.round(item.confidence * 100)}%`;
    canvasContext.save();
    canvasContext.strokeStyle = style.color;
    canvasContext.lineWidth = Math.max(2, Math.min(5, elements.imageCanvas.width / 320));
    canvasContext.setLineDash(style.dash);
    canvasContext.strokeRect(x1, y1, width, height);
    canvasContext.setLineDash([]);
    canvasContext.font = `600 ${Math.max(12, Math.min(18, elements.imageCanvas.width / 45))}px Arial`;
    const textWidth = canvasContext.measureText(text).width;
    const tagWidth = Math.min(elements.imageCanvas.width, textWidth + 12);
    const tagHeight = Math.max(22, elements.imageCanvas.width / 38);
    const tagX = Math.max(0, Math.min(x1, elements.imageCanvas.width - tagWidth));
    const tagY = y1 - tagHeight >= 0 ? y1 - tagHeight : Math.min(elements.imageCanvas.height - tagHeight, y1);
    canvasContext.fillStyle = style.color;
    canvasContext.fillRect(tagX, tagY, tagWidth, tagHeight);
    canvasContext.fillStyle = '#ffffff';
    canvasContext.textBaseline = 'middle';
    canvasContext.fillText(text, tagX + 6, tagY + tagHeight / 2, tagWidth - 10);
    canvasContext.restore();
  }

  function drawPreview(detections, suppressed = []) {
    if (!previewImage) return;
    const width = previewImage.naturalWidth;
    const height = previewImage.naturalHeight;
    elements.imageCanvas.width = width;
    elements.imageCanvas.height = height;
    canvasContext.clearRect(0, 0, width, height);
    canvasContext.drawImage(previewImage, 0, 0, width, height);
    detections.forEach((item) => drawBox(item));
    suppressed.forEach((item) => drawBox(item, true));
  }

  function detectionDescription(item, suppressed = false) {
    const label = CLASS_LABELS[item.class_name] ?? item.class_name;
    if (suppressed) {
      const percent = Math.round((item.wearer_box_coverage_by_depiction_union ?? 0) * 100);
      return `${label} · đã loại bởi poster/ảnh/màn hình (${percent}% vùng giao). Không tính.`;
    }
    if (WORN_CLASSES.has(item.class_name)) {
      return item.source_status === 'uncertain_partial_depiction_overlap'
        ? `${label} · giao vùng hiển thị, chưa xác định và không tính.`
        : `${label} · chưa xác minh nguồn, không tính.`;
    }
    if (item.class_name === 'depiction_region') return `${label} · ranh giới nguồn hiển thị do mô hình phát hiện.`;
    return `${label} · nhãn mô hình, không phải số đếm người đội mũ.`;
  }

  function boxPositionDescription(item) {
    if (!previewImage) return '';
    const [x1, y1, x2, y2] = item.box_xyxy;
    const percent = (coordinate, extent) => ((coordinate / extent) * 100).toLocaleString('vi-VN', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    });
    return `Vị trí trong ảnh từ góc trên trái: từ trái ${percent(x1, previewImage.naturalWidth)}–${percent(x2, previewImage.naturalWidth)}%, từ trên ${percent(y1, previewImage.naturalHeight)}–${percent(y2, previewImage.naturalHeight)}%.`;
  }

  function renderDetectionRows(detections, suppressed) {
    const rows = [
      ...detections.map((item) => ({ item, suppressed: false })),
      ...suppressed.map((item) => ({ item, suppressed: true })),
    ];
    if (!rows.length) {
      const empty = document.createElement('li');
      empty.className = 'detection-row detection-empty-row';
      empty.textContent = 'Không có hộp vượt ngưỡng trong kết quả. Điều này không chứng minh ảnh không có người đội mũ.';
      elements.detectionList.replaceChildren(empty);
      return;
    }
    const listItems = rows.map(({ item, suppressed: wasSuppressed }) => {
      const row = document.createElement('li');
      row.className = 'detection-row';
      row.style.setProperty('--detection-color', boxStyle(item, wasSuppressed).color);
      const dot = document.createElement('span');
      dot.className = 'detection-dot';
      dot.setAttribute('aria-hidden', 'true');
      const copy = document.createElement('span');
      copy.className = 'detection-copy';
      const name = document.createElement('strong');
      name.textContent = CLASS_LABELS[item.class_name] ?? item.class_name;
      const description = document.createElement('span');
      description.textContent = `${detectionDescription(item, wasSuppressed)} ${boxPositionDescription(item)}`;
      const confidence = document.createElement('span');
      confidence.className = 'detection-confidence';
      confidence.textContent = `${Math.round(item.confidence * 100)}%`;
      copy.append(name, description);
      row.append(dot, copy, confidence);
      return row;
    });
    elements.detectionList.replaceChildren(...listItems);
  }

  function renderResults(payload) {
    const detections = Array.isArray(payload.detections) ? payload.detections : [];
    const suppressed = Array.isArray(payload.suppressed_wearer_candidates)
      ? payload.suppressed_wearer_candidates : [];
    const candidates = Array.isArray(payload.wearer_candidates_for_review)
      ? payload.wearer_candidates_for_review : [];
    const uncertain = Array.isArray(payload.uncertain_wearer_candidates)
      ? payload.uncertain_wearer_candidates : [];

    drawPreview(detections, suppressed);
    elements.confirmedCount.textContent = '0';
    elements.candidateCount.textContent = String(candidates.length + uncertain.length);
    elements.suppressedCount.textContent = String(suppressed.length);
    renderDetectionRows(detections, suppressed);
    elements.resultSummary.hidden = false;
    elements.requestError.hidden = true;
    elements.requestStatus.textContent = 'Suy luận hoàn tất. Rà toàn ảnh trước khi kết luận về nguồn của người được phát hiện.';
    elements.resultBadge.textContent = 'Cần rà nguồn';
    elements.resultBadge.dataset.state = 'success';
  }

  function hasSafePredictionContract(payload, expectedConfidence) {
    if (payload?.wearer_count !== 0
      || payload?.review_required !== true
      || payload?.source_status !== 'unverified'
      || !Array.isArray(payload.raw_detections_for_review)
      || !Array.isArray(payload.detections)
      || !Array.isArray(payload.suppressed_wearer_candidates)
      || !Array.isArray(payload.uncertain_wearer_candidates)
      || !Array.isArray(payload.wearer_candidates_for_review)
      || !Number.isFinite(payload.confidence_threshold)
      || payload.confidence_threshold < expectedConfidence
      || payload.confidence_threshold > 1.0
      || payload.image?.width !== previewImage?.naturalWidth
      || payload.image?.height !== previewImage?.naturalHeight) return false;

    const isValidDetectionShape = (item) => {
      if (!item || !Object.hasOwn(CLASS_LABELS, item.class_name)
        || !Number.isFinite(item.confidence) || item.confidence < 0 || item.confidence > 1
        || !Array.isArray(item.box_xyxy) || item.box_xyxy.length !== 4
        || !item.box_xyxy.every(Number.isFinite)) return false;
      const [x1, y1, x2, y2] = item.box_xyxy;
      if (x1 < 0 || y1 < 0 || x2 > previewImage.naturalWidth || y2 > previewImage.naturalHeight
        || x2 <= x1 || y2 <= y1) return false;
      return true;
    };
    const isValidDetection = (item) => {
      if (!isValidDetectionShape(item)) return false;
      if (WORN_CLASSES.has(item.class_name)) {
        if (item.counted !== false) return false;
      }
      return true;
    };
    const isValidRawDetection = (item) => isValidDetectionShape(item)
      && item.confidence >= MIN_INFERENCE_CONFIDENCE;
    if (!payload.raw_detections_for_review.every(isValidRawDetection)
      || !payload.detections.every(isValidDetection)
      || !payload.suppressed_wearer_candidates.every(isValidDetection)
      || !payload.uncertain_wearer_candidates.every(isValidDetection)
      || !payload.wearer_candidates_for_review.every(isValidDetection)) return false;

    const rawDepictionRegions = payload.raw_detections_for_review
      .filter((item) => item.class_name === 'depiction_region');
    const depictionRegions = rawDepictionRegions
      .map((item) => item.box_xyxy);
    const rectangleUnionArea = (rectangles) => {
      const valid = rectangles.filter((box) => box[2] > box[0] && box[3] > box[1]);
      const xEdges = [...new Set(valid.flatMap((box) => [box[0], box[2]]))]
        .sort((first, second) => first - second);
      let total = 0;
      for (let index = 0; index < xEdges.length - 1; index += 1) {
        const left = xEdges[index];
        const right = xEdges[index + 1];
        if (right <= left) continue;
        const intervals = valid
          .filter((box) => box[0] < right && box[2] > left)
          .map((box) => [box[1], box[3]])
          .sort((first, second) => first[0] - second[0] || first[1] - second[1]);
        let coveredY = 0;
        if (intervals.length) {
          let start = intervals[0][0];
          let end = intervals[0][1];
          for (const [nextStart, nextEnd] of intervals.slice(1)) {
            if (nextStart > end) {
              coveredY += end - start;
              start = nextStart;
              end = nextEnd;
            } else {
              end = Math.max(end, nextEnd);
            }
          }
          coveredY += end - start;
        }
        total += (right - left) * coveredY;
      }
      return total;
    };
    const overlapFor = (item) => {
      const box = item.box_xyxy;
      const boxArea = (box[2] - box[0]) * (box[3] - box[1]);
      const centerX = (box[0] + box[2]) / 2;
      const centerY = (box[1] + box[3]) / 2;
      const centerInside = depictionRegions.some((region) => (
        region[0] <= centerX && centerX <= region[2]
        && region[1] <= centerY && centerY <= region[3]
      ));
      const intersections = depictionRegions
        .map((region) => [
          Math.max(box[0], region[0]),
          Math.max(box[1], region[1]),
          Math.min(box[2], region[2]),
          Math.min(box[3], region[3]),
        ])
        .filter((intersection) => intersection[2] > intersection[0]
          && intersection[3] > intersection[1]);
      return { centerInside, coverage: rectangleUnionArea(intersections) / boxArea };
    };
    const reportedCoverageMatches = (item, coverage, required) => {
      const reported = item.wearer_box_coverage_by_depiction_union;
      if (reported === undefined) return !required;
      return Number.isFinite(reported)
        && reported >= 0
        && reported <= 1.000001
        && Math.abs(reported - coverage) <= 1e-6;
    };
    const matchesGroup = (item, group) => {
      if (!WORN_CLASSES.has(item.class_name)) return false;
      const { centerInside, coverage } = overlapFor(item);
      if (group === 'suppressed') {
        const expectedReason = centerInside
          ? 'wearer_center_inside_depiction_region'
          : coverage >= 0.5
            ? 'at_least_half_of_wearer_box_covered_by_depiction_union'
            : null;
        return expectedReason !== null
          && item.suppression_reason === expectedReason
          && reportedCoverageMatches(item, coverage, true);
      }
      if (centerInside || coverage >= 0.5) return false;
      if (group === 'uncertain') {
        return coverage > 0
          && item.source_status === 'uncertain_partial_depiction_overlap'
          && reportedCoverageMatches(item, coverage, true);
      }
      return coverage === 0
        && item.source_status === 'unverified'
        && reportedCoverageMatches(item, coverage, false);
    };

    const predictionKey = (item) => JSON.stringify([item.class_name, item.confidence, item.box_xyxy]);
    const hasUniquePredictionKeys = (items) => {
      const keys = items.map(predictionKey);
      return new Set(keys).size === keys.length;
    };
    const hasSamePredictionMultiset = (left, right) => {
      if (left.length !== right.length) return false;
      const remaining = new Map();
      left.forEach((item) => {
        const key = predictionKey(item);
        remaining.set(key, (remaining.get(key) ?? 0) + 1);
      });
      for (const item of right) {
        const key = predictionKey(item);
        const count = remaining.get(key) ?? 0;
        if (count === 0) return false;
        if (count === 1) remaining.delete(key);
        else remaining.set(key, count - 1);
      }
      return remaining.size === 0;
    };
    const rawHardhatDetections = payload.raw_detections_for_review
      .filter((item) => WORN_CLASSES.has(item.class_name)
        && item.confidence >= payload.confidence_threshold);
    const expectedGroups = { candidate: [], uncertain: [], suppressed: [] };
    rawHardhatDetections.forEach((item) => {
      const { centerInside, coverage } = overlapFor(item);
      if (centerInside || coverage >= 0.5) expectedGroups.suppressed.push(item);
      else if (coverage > 0) expectedGroups.uncertain.push(item);
      else expectedGroups.candidate.push(item);
    });
    const hardhatDetections = payload.detections.filter((item) => WORN_CLASSES.has(item.class_name));
    const allReportedWearerCandidates = [
      ...payload.wearer_candidates_for_review,
      ...payload.uncertain_wearer_candidates,
      ...payload.suppressed_wearer_candidates,
    ];
    if (!hasUniquePredictionKeys(payload.raw_detections_for_review)
      || !hasUniquePredictionKeys(hardhatDetections)
      || !hasUniquePredictionKeys(allReportedWearerCandidates)
      || !hasSamePredictionMultiset(rawDepictionRegions, payload.detections.filter((item) => (
        item.class_name === 'depiction_region'
      )))
      || !hasSamePredictionMultiset(expectedGroups.candidate, payload.wearer_candidates_for_review)
      || !hasSamePredictionMultiset(expectedGroups.uncertain, payload.uncertain_wearer_candidates)
      || !hasSamePredictionMultiset(expectedGroups.suppressed, payload.suppressed_wearer_candidates)
      || !hasSamePredictionMultiset(
        [...expectedGroups.candidate, ...expectedGroups.uncertain],
        hardhatDetections,
      )) return false;

    return payload.detections.every((item) => (
      !WORN_CLASSES.has(item.class_name)
      || matchesGroup(item, item.source_status === 'uncertain_partial_depiction_overlap'
        ? 'uncertain' : 'candidate')
    ))
      && payload.suppressed_wearer_candidates.every((item) => matchesGroup(item, 'suppressed'))
      && payload.uncertain_wearer_candidates.every((item) => matchesGroup(item, 'uncertain'))
      && payload.wearer_candidates_for_review.every((item) => matchesGroup(item, 'candidate'));
  }

  function showRequestError(status, detail) {
    if (status === 503) {
      setApiStatus(
        'model-unavailable',
        'API đã phản hồi · mô hình chưa sẵn sàng',
        modelUnavailableMessage(detail && typeof detail === 'object' ? detail.code : null),
      );
    } else if (status === 0) {
      setApiStatus('offline', 'Không kết nối được inference API');
    } else if (status === 404 || status === 501) {
      setApiStatus('model-unavailable', 'API có phản hồi · endpoint suy luận chưa khả dụng', `Máy chủ trả HTTP ${status}. Ảnh chưa được xử lý.`, ['alive', 'blocked']);
    } else if (status >= 500) {
      setApiStatus('model-unavailable', 'API có phản hồi · suy luận gặp lỗi', `Máy chủ trả HTTP ${status}. Kiểm tra trạng thái và log dịch vụ.`, ['alive', 'blocked']);
    }
    const message = status === 503
      ? modelUnavailableMessage(detail && typeof detail === 'object' ? detail.code : null)
      : status === 500
        ? 'Suy luận thất bại trên máy chủ API. Kiểm tra log dịch vụ.'
        : typeof detail === 'string' ? detail : `Máy chủ trả HTTP ${status}.`;
    elements.requestError.textContent = message;
    elements.requestError.hidden = false;
    elements.resultSummary.hidden = true;
    elements.requestStatus.textContent = 'Không nhận được kết quả suy luận.';
    elements.resultBadge.textContent = 'Có lỗi';
    elements.resultBadge.dataset.state = 'error';
  }

  function showInferenceTimeout() {
    elements.requestError.textContent = 'Không nhận được kết quả trong 120 giây. Trình duyệt đã dừng chờ, nhưng API có thể vẫn đang xử lý ảnh; kiểm tra trạng thái trước khi gửi lại.';
    elements.requestError.hidden = false;
    elements.resultSummary.hidden = true;
    elements.requestStatus.textContent = 'Đã hết thời gian chờ nhận kết quả.';
    elements.resultBadge.textContent = 'Quá thời gian';
    elements.resultBadge.dataset.state = 'error';
  }

  async function runInference() {
    if (!selectedFile || !apiReady) return;
    activeRequest?.abort();
    const controller = new AbortController();
    activeRequest = controller;
    let timedOut = false;
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, INFERENCE_TIMEOUT_MS);
    elements.runButton.disabled = true;
    elements.runLabel.textContent = 'Đang chạy…';
    elements.requestError.hidden = true;
    elements.resultSummary.hidden = true;
    elements.resultBadge.textContent = 'Đang suy luận';
    elements.resultBadge.dataset.state = '';
    elements.requestStatus.textContent = 'Đang gửi ảnh lên máy chủ API và chạy mô hình.';
    drawPreview([]);

    const form = new FormData();
    const extension = selectedFile.name.split('.').pop()?.toLowerCase() ?? '';
    const uploadMimeType = ALLOWED_IMAGE_MIMES.has(selectedFile.type)
      ? selectedFile.type : IMAGE_MIMES_BY_EXTENSION[extension];
    const uploadBlob = selectedFile.type === uploadMimeType
      ? selectedFile : new Blob([selectedFile], { type: uploadMimeType });
    form.append('image', uploadBlob, selectedFile.name);
    const confidence = Number(elements.confidenceInput.value) / 100;
    try {
      const response = await fetch(`/predict?confidence=${confidence.toFixed(2)}`, {
        method: 'POST',
        body: form,
        signal: controller.signal,
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json().catch(() => ({}));
      if (activeRequest !== controller) return;
      if (!response.ok) {
        showRequestError(response.status, payload.detail ?? 'Không thể xử lý ảnh.');
        return;
      }
      if (!hasSafePredictionContract(payload, confidence)) {
        showRequestError(502, 'Phản hồi API không đạt chính sách an toàn: cần wearer_count=0, review_required=true và source_status=unverified. Kết quả đã bị ẩn.');
        return;
      }
      setApiStatus('ready', 'API xác nhận mô hình đã sẵn sàng');
      renderResults(payload);
    } catch (error) {
      if (activeRequest !== controller) return;
      if (error.name === 'AbortError') {
        if (timedOut) showInferenceTimeout();
        return;
      }
      showRequestError(0, 'Không kết nối được API. Hãy mở trang này cùng origin với dịch vụ đang phục vụ API.');
    } finally {
      window.clearTimeout(timeoutId);
      if (activeRequest === controller) {
        activeRequest = null;
        elements.runButton.disabled = !selectedFile || !apiReady;
        elements.runLabel.textContent = 'Chạy kiểm tra';
      }
    }
  }

  elements.fileInput.addEventListener('change', () => loadSelectedFile(elements.fileInput.files?.[0]));
  elements.recheckApiButton.addEventListener('click', checkApi);
  elements.removeFile.addEventListener('click', resetSelectedFile);
  elements.runButton.addEventListener('click', runInference);
  elements.confidenceInput.addEventListener('input', () => {
    elements.confidenceValue.value = `${elements.confidenceInput.value}%`;
  });
  elements.dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    elements.dropZone.classList.add('is-dragging');
  });
  elements.dropZone.addEventListener('dragleave', () => elements.dropZone.classList.remove('is-dragging'));
  elements.dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove('is-dragging');
    loadSelectedFile(event.dataTransfer?.files?.[0]);
  });
  elements.dropZone.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      elements.fileInput.click();
    }
  });
  window.addEventListener('beforeunload', () => {
    activeRequest?.abort();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  });
  window.addEventListener('focus', () => {
    if (!activeRequest) checkApi();
  });

  clearResults();
  checkApi();
})();
