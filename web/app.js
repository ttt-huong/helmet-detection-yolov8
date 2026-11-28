(() => {
  const categories = [
    { id: 0, key: 'hard_hat_worn', name: 'Mũ bảo hộ công trường', group: 'worn', color: '#25845b' },
    { id: 1, key: 'traffic_helmet_worn', name: 'Mũ bảo hiểm giao thông', group: 'worn', color: '#4f7eb4' },
    { id: 2, key: 'cap_worn', name: 'Mũ lưỡi trai / kê-pi', group: 'worn', color: '#d18b4e' },
    { id: 3, key: 'beanie_worn', name: 'Mũ len', group: 'worn', color: '#8a70b7' },
    { id: 4, key: 'bare_head', name: 'Đầu trần', group: 'worn', color: '#c26f76' },
    { id: 5, key: 'depicted_hat', name: 'Mũ trong hình ảnh', group: 'depicted', color: '#d1804a' },
    { id: 6, key: 'loose_hat', name: 'Mũ rời', group: 'depicted', color: '#788398' },
    { id: 7, key: 'depiction_region', name: 'Poster / ảnh / màn hình', group: 'depicted', color: '#ba6659' },
  ];
  const byKey = Object.fromEntries(categories.map((item) => [item.key, item]));
  const wornClassKeys = new Set(categories.filter((item) => item.key.endsWith('_worn')).map((item) => item.key));
  const targetWornClassKeys = new Set(['hard_hat_worn']);
  const sourceDependentHeadClassKeys = new Set([...wornClassKeys, 'bare_head']);
  const depictionSceneTypes = new Set(['depiction_only', 'mixed_scene']);
  const allowedDepictionSurfaceTypes = new Set(['poster', 'printed_photo', 'screen', 'other_depiction']);
  const depictionSurfaceTypeOrder = ['poster', 'printed_photo', 'screen', 'other_depiction'];
  const depictionSurfaceLabels = {
    poster: 'Poster / áp phích',
    printed_photo: 'Ảnh in',
    screen: 'Màn hình',
    other_depiction: 'Hình ảnh hiển thị khác',
  };
  const isWornClass = (classKey) => wornClassKeys.has(classKey);
  const isTargetWornClass = (classKey) => targetWornClassKeys.has(classKey);
  const isSourceDependentHeadClass = (classKey) => sourceDependentHeadClassKeys.has(classKey);
  const acceptedMimeTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
  const maxFileBytes = 10 * 1024 * 1024;
  const maxSessionBytes = 50 * 1024 * 1024;
  const maxSessionPixels = 48_000_000;
  const maxSessionImages = 20;
  const maxImagePixels = 24_000_000;
  const draftStorageKey = 'helmet-vision.review-draft.v1';
  const draftFormat = 'helmet-vision-labeler-draft-v1';
  const imageReviewStatuses = new Set(['pending', 'reviewed_empty', 'labels_need_review', 'reviewed_labeled']);
  const uuidV4Pattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const elements = {
    addSmall: document.querySelector('#add-images-small'),
    annotationList: document.querySelector('#annotation-list'),
    annotationTotal: document.querySelector('#annotation-total'),
    assetCount: document.querySelector('#asset-count'),
    assetList: document.querySelector('#asset-list'),
    boxCount: document.querySelector('#box-count'),
    boxHelp: document.querySelector('#box-help'),
    canvas: document.querySelector('#image-canvas'),
    canvasEmpty: document.querySelector('#canvas-empty'),
    canvasMode: document.querySelector('#canvas-mode'),
    clearImages: document.querySelector('#clear-images'),
    deleteBox: document.querySelector('#delete-box'),
    dismissNotice: document.querySelector('#dismiss-notice'),
    discardDraft: document.querySelector('#discard-draft'),
    datasetMetadata: document.querySelector('#dataset-metadata'),
    depictionRegionSurfaceGroup: document.querySelector('#depiction-region-surface-group'),
    depictionRegionSurfaceType: document.querySelector('#depiction-region-surface-type'),
    depictionRegionSurfaceError: document.querySelector('#depiction-region-surface-error'),
    dropZone: document.querySelector('#drop-zone'),
    emptyAssets: document.querySelector('#empty-assets'),
    exportJson: document.querySelector('#export-json'),
    exportOverlay: document.querySelector('#export-overlay'),
    exportOverlayStatus: document.querySelector('#overlay-export-status'),
    fileInput: document.querySelector('#file-input'),
    draftStatus: document.querySelector('#draft-status'),
    guideDialog: document.querySelector('#guide-dialog'),
    guideDone: document.querySelector('#guide-done'),
    imageDimensions: document.querySelector('#image-dimensions'),
    imageAttribution: document.querySelector('#image-attribution'),
    imageGroupId: document.querySelector('#image-group-id'),
    imageLicenseId: document.querySelector('#image-license-id'),
    imageReviewStatus: document.querySelector('#image-review-status'),
    imageReviewStatusTitle: document.querySelector('#image-review-title'),
    imageRightsBasis: document.querySelector('#image-rights-basis'),
    imageSceneType: document.querySelector('#image-scene-type'),
    imageSourceReference: document.querySelector('#image-source-reference'),
    imageSplit: document.querySelector('#image-split'),
    imageTrainingUse: document.querySelector('#image-training-use'),
    depictionSurfaceError: document.querySelector('#depiction-surface-error'),
    depictionSurfaceTypes: Array.from(document.querySelectorAll('input[name="depiction_surface_type"]')),
    depictionSurfaceCountInputs: Array.from(document.querySelectorAll('input[name="depiction_surface_count"]')),
    nonpersonLabels: document.querySelector('#nonperson-labels'),
    openGuide: document.querySelector('#open-guide'),
    markReviewedNoLabels: document.querySelector('#mark-reviewed-no-labels'),
    markReviewedWithLabels: document.querySelector('#mark-reviewed-with-labels'),
    reviewCount: document.querySelector('#review-count'),
    restoreDraft: document.querySelector('#restore-draft'),
    restoreFileInput: document.querySelector('#restore-file-input'),
    reviewScene: document.querySelector('#review-scene'),
    otherSceneReviewRow: document.querySelector('#other-scene-review-row'),
    otherSceneReview: document.querySelector('#other-scene-review'),
    sceneReviewTitle: document.querySelector('#scene-review-title'),
    sceneReviewStatus: document.querySelector('#scene-review-status'),
    toast: document.querySelector('#toast'),
    wornLabels: document.querySelector('#worn-labels'),
    zoomIn: document.querySelector('#zoom-in'),
    zoomLevel: document.querySelector('#zoom-level'),
    zoomOut: document.querySelector('#zoom-out'),
    closeGuide: document.querySelector('#close-guide'),
  };
  const context = elements.canvas.getContext('2d');
  const files = [];
  let activeFileId = null;
  let activeClass = categories[0].key;
  let selectedBoxId = null;
  let nextDepictionSurfaceId = '';
  let dragAction = null;
  let toastTimer = null;
  let draftSaveTimer = null;
  let draftSaveRevision = 0;
  let draftDirty = false;
  let savedDraft = null;
  let draftAvailable = false;
  let invalidDraftMessage = '';
  let pendingRestoreDraft = null;
  let pendingRestoreRevision = null;
  let pendingRestoreHadUnsavedChanges = false;
  let restoreSelectionPending = false;
  let draftRestoreInProgress = false;
  let preserveStoredDraftAfterRestoreFailure = false;
  let pendingImageAddCount = 0;
  let zoom = 1;

  function createFile(file) {
    return {
      id: crypto.randomUUID(),
      name: file.name,
      url: URL.createObjectURL(file),
      blob: file,
      image: null,
      sha256: null,
      sha256Promise: null,
      annotations: [],
      imageReviewStatus: 'pending',
      frameSourceStatus: 'review_required',
      frameSourceReviewedAt: null,
      groupId: '',
      sceneType: '',
      otherSceneNoDepictedPeopleReviewed: false,
      depictionSurfaceTypes: [],
      depictionSurfaceCounts: Object.fromEntries(depictionSurfaceTypeOrder.map((surfaceType) => [surfaceType, 0])),
      depictionSurfaces: [],
      split: '',
      trainingUse: 'unknown',
      rightsBasis: '',
      sourceReference: '',
      licenseId: '',
      attribution: '',
    };
  }

  function imageReviewStatusFor(file) {
    if (file.annotations.length) {
      return file.frameSourceStatus === 'clear'
        && file.imageReviewStatus === 'reviewed_labeled'
        ? 'reviewed_labeled' : 'labels_need_review';
    }
    return file.frameSourceStatus === 'clear' && file.imageReviewStatus === 'reviewed_empty'
      ? 'reviewed_empty' : 'pending';
  }

  async function sha256Blob(blob) {
    const subtle = globalThis.crypto?.subtle;
    if (!subtle || typeof blob.arrayBuffer !== 'function') {
      throw new Error('WebCrypto SHA-256 không khả dụng trong trình duyệt này.');
    }
    const digest = await subtle.digest('SHA-256', await blob.arrayBuffer());
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  function getFileSha256(file) {
    if (file.sha256) return Promise.resolve(file.sha256);
    if (!file.sha256Promise) {
      file.sha256Promise = sha256Blob(file.blob)
        .then((digest) => {
          file.sha256 = digest;
          return digest;
        })
        .catch((error) => {
          file.sha256Promise = null;
          throw error;
        });
    }
    return file.sha256Promise;
  }

  function setDraftStatus(message, state = 'info') {
    elements.draftStatus.textContent = message;
    elements.draftStatus.dataset.state = state;
  }

  function updateDraftControls() {
    elements.restoreDraft.hidden = !draftAvailable;
    elements.discardDraft.hidden = !draftAvailable;
    elements.restoreDraft.disabled = !draftAvailable || !!invalidDraftMessage;
    if (invalidDraftMessage) {
      setDraftStatus(invalidDraftMessage + ' Có thể xóa bản nháp hỏng để bắt đầu batch mới.', 'error');
    } else if (!draftAvailable) {
      setDraftStatus('Bản nháp tự lưu cục bộ trong trình duyệt; ảnh gốc cần được chọn lại khi khôi phục.', 'info');
    }
  }

  function draftImageKey(name, size, width, height, sha256) {
    return JSON.stringify([name, size, width, height, sha256]);
  }

  function validateDraftSnapshot(draft) {
    if (!draft || typeof draft !== 'object' || draft.format !== draftFormat
        || typeof draft.saved_at !== 'string' || Number.isNaN(Date.parse(draft.saved_at))
        || typeof draft.active_file_id !== 'string' || !uuidV4Pattern.test(draft.active_file_id)
        || !Array.isArray(draft.classes)
        || JSON.stringify(draft.classes) !== JSON.stringify(categories.map(({ id, key }) => ({ id, name: key })))) {
      return 'Bản nháp không đúng phiên bản hoặc ontology hiện tại.';
    }
    if (!Array.isArray(draft.images) || draft.images.length < 1 || draft.images.length > maxSessionImages) {
      return 'Bản nháp không có danh sách ảnh hợp lệ hoặc vượt giới hạn 20 ảnh.';
    }

    const imageIds = new Set();
    const imageKeys = new Set();
    const fileNames = new Set();
    const fingerprints = new Set();
    let totalBytes = 0;
    let totalPixels = 0;
    for (const record of draft.images) {
      if (!record || typeof record !== 'object'
          || typeof record.image_id !== 'string'
          || !uuidV4Pattern.test(record.image_id)
          || typeof record.file_name !== 'string' || !record.file_name.trim()
          || /[\\/]/.test(record.file_name)
          || !Number.isSafeInteger(record.file_size) || record.file_size < 0 || record.file_size > maxFileBytes
          || !Number.isSafeInteger(record.width) || record.width <= 0
          || !Number.isSafeInteger(record.height) || record.height <= 0
          || record.width * record.height > maxImagePixels
          || typeof record.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(record.sha256)
          || !Array.isArray(record.annotations)) {
        return 'Bản nháp có thông tin ảnh không hợp lệ.';
      }
      totalBytes += record.file_size;
      totalPixels += record.width * record.height;
      const imageId = record.image_id.toLowerCase();
      const key = draftImageKey(record.file_name, record.file_size, record.width, record.height, record.sha256);
      const fileNameKey = record.file_name.toLowerCase();
      if (imageIds.has(imageId) || imageKeys.has(key) || fileNames.has(fileNameKey)
          || fingerprints.has(record.sha256)) {
        return 'Bản nháp có ảnh trùng tên hoặc trùng nội dung SHA-256, không thể khôi phục an toàn.';
      }
      imageIds.add(imageId);
      imageKeys.add(key);
      fileNames.add(fileNameKey);
      fingerprints.add(record.sha256);

      if (!['', 'depiction_only', 'mixed_scene', 'other'].includes(record.scene_type)
          || !['', 'train', 'val', 'test'].includes(record.split)
          || (record.image_review_status !== undefined && !imageReviewStatuses.has(record.image_review_status))
          || !['unknown', 'approved', 'not_allowed'].includes(record.training_use)
          || !['', 'owned', 'permission', 'license', 'public_domain'].includes(record.rights_basis)
          || !['clear', 'review_required'].includes(record.frame_source_status)
          || (record.frame_source_reviewed_at !== null
            && (typeof record.frame_source_reviewed_at !== 'string'
              || Number.isNaN(Date.parse(record.frame_source_reviewed_at))))
          || (record.frame_source_status === 'clear' && !record.frame_source_reviewed_at)
          || (record.frame_source_status === 'review_required' && record.frame_source_reviewed_at !== null)
          || !Array.isArray(record.depiction_surface_types)
          || record.depiction_surface_types.some((surfaceType) => !allowedDepictionSurfaceTypes.has(surfaceType))
          || new Set(record.depiction_surface_types).size !== record.depiction_surface_types.length
          || !Array.isArray(record.depiction_surfaces)
          || !record.depiction_surface_counts || typeof record.depiction_surface_counts !== 'object'
          || Array.isArray(record.depiction_surface_counts)
          || !Array.isArray(record.annotations)
          || typeof record.group_id !== 'string'
          || typeof record.source_reference !== 'string'
          || typeof record.license_id !== 'string'
          || typeof record.attribution !== 'string') {
        return `Bản nháp có metadata không hợp lệ cho ảnh ${record.file_name}.`;
      }

      const surfaceIds = new Set();
      for (const surface of record.depiction_surfaces) {
        if (!surface || typeof surface.surface_id !== 'string' || !surface.surface_id
            || !allowedDepictionSurfaceTypes.has(surface.surface_type) || surfaceIds.has(surface.surface_id)) {
          return `Bản nháp có inventory bề mặt không hợp lệ cho ảnh ${record.file_name}.`;
        }
        surfaceIds.add(surface.surface_id);
      }
      const inventoryTypes = new Set(record.depiction_surfaces.map((surface) => surface.surface_type));
      if (record.depiction_surface_types.some((surfaceType) => !inventoryTypes.has(surfaceType))
          || [...inventoryTypes].some((surfaceType) => !record.depiction_surface_types.includes(surfaceType))) {
        return `Bản nháp có loại bề mặt không khớp inventory cho ảnh ${record.file_name}.`;
      }
      for (const surfaceType of depictionSurfaceTypeOrder) {
        const count = record.depiction_surface_counts[surfaceType];
        if (!Number.isInteger(count) || count < 0 || count > 20
            || (record.depiction_surface_types.includes(surfaceType) && count < 1)
            || (!record.depiction_surface_types.includes(surfaceType) && count !== 0)
            || record.depiction_surfaces.filter((surface) => surface.surface_type === surfaceType).length !== count) {
          return `Bản nháp có số lượng bề mặt không khớp cho ảnh ${record.file_name}.`;
        }
      }
      const annotationIds = new Set();
      for (const annotation of record.annotations) {
        if (!annotation || typeof annotation.id !== 'string' || !uuidV4Pattern.test(annotation.id)
            || !byKey[annotation.classKey] || annotationIds.has(annotation.id.toLowerCase())
            || !['confirmed', 'uncertain', 'reviewed_confirmed'].includes(annotation.reviewState)
            || !['x', 'y', 'width', 'height'].every((keyName) => Number.isFinite(annotation[keyName]))
            || annotation.x < 0 || annotation.y < 0 || annotation.width <= 0 || annotation.height <= 0
            || annotation.x + annotation.width > 1 || annotation.y + annotation.height > 1
            || (annotation.classKey === 'depiction_region'
              && typeof annotation.depictionSurfaceId !== 'string')) {
          return `Bản nháp có annotation không hợp lệ cho ảnh ${record.file_name}.`;
        }
        annotationIds.add(annotation.id.toLowerCase());
      }

      const reviewFile = {
        sceneType: record.scene_type,
        otherSceneNoDepictedPeopleReviewed: record.other_scene_no_depicted_people_reviewed,
        frameSourceStatus: record.frame_source_status,
        depictionSurfaceTypes: record.depiction_surface_types,
        depictionSurfaces: record.depiction_surfaces.map((surface) => ({
          surfaceId: surface.surface_id,
          surfaceType: surface.surface_type,
        })),
        annotations: record.annotations,
      };
      const sourceGateIssue = !record.scene_type
        || (record.scene_type === 'other' && !record.other_scene_no_depicted_people_reviewed)
        || hasContradictoryDepictionMetadata(reviewFile)
        || needsDepictionSurfaceType(reviewFile)
        || !!getDepictionRegionCoverageIssue(reviewFile);
      if (record.frame_source_status === 'clear' && sourceGateIssue) {
        return `Bản nháp ghi nguồn đã xác minh nhưng thiếu scene/surface gate cho ảnh ${record.file_name}.`;
      }
    }
    if (totalBytes > maxSessionBytes || totalPixels > maxSessionPixels
        || !imageIds.has(draft.active_file_id.toLowerCase())) {
      return 'Bản nháp vượt giới hạn phiên hoặc active_file_id không trỏ tới ảnh trong phiên.';
    }
    return '';
  }

  function loadSavedDraft() {
    let raw;
    try {
      raw = localStorage.getItem(draftStorageKey);
    } catch (error) {
      draftAvailable = false;
      invalidDraftMessage = '';
      setDraftStatus('Không đọc được bộ nhớ cục bộ của trình duyệt. Hãy xuất JSON batch thường xuyên.', 'error');
      return;
    }
    if (!raw) {
      draftAvailable = false;
      invalidDraftMessage = '';
      updateDraftControls();
      return;
    }

    draftAvailable = true;
    try {
      savedDraft = JSON.parse(raw);
      invalidDraftMessage = validateDraftSnapshot(savedDraft);
      if (invalidDraftMessage) {
        savedDraft = null;
        updateDraftControls();
        return;
      }
      const savedAt = new Date(savedDraft.saved_at);
      const timeLabel = Number.isNaN(savedAt.valueOf()) ? '' : ` · ${savedAt.toLocaleString()}`;
      setDraftStatus(`Có bản nháp ${savedDraft.images.length} ảnh được lưu cục bộ${timeLabel}. Chọn lại đúng ảnh gốc để khôi phục.`, 'saved');
      updateDraftControls();
    } catch (error) {
      savedDraft = null;
      invalidDraftMessage = 'Không đọc được bản nháp cục bộ.';
      updateDraftControls();
    }
  }

  function createDraftSnapshot() {
    return {
      format: draftFormat,
      saved_at: new Date().toISOString(),
      classes: categories.map(({ id, key }) => ({ id, name: key })),
      active_file_id: activeFileId,
      images: files.map((file) => ({
        image_id: file.id,
        file_name: file.name,
        file_size: file.blob.size,
        sha256: file.sha256,
        width: file.image.naturalWidth,
        height: file.image.naturalHeight,
        annotations: file.annotations.map((annotation) => ({ ...annotation })),
        image_review_status: imageReviewStatusFor(file),
        frame_source_status: file.frameSourceStatus,
        frame_source_reviewed_at: file.frameSourceReviewedAt,
        group_id: file.groupId,
        scene_type: file.sceneType,
        other_scene_no_depicted_people_reviewed: file.otherSceneNoDepictedPeopleReviewed,
        depiction_surface_types: [...file.depictionSurfaceTypes],
        depiction_surface_counts: { ...file.depictionSurfaceCounts },
        depiction_surfaces: file.depictionSurfaces.map((surface) => ({
          surface_id: surface.surfaceId,
          surface_type: surface.surfaceType,
        })),
        split: file.split,
        training_use: file.trainingUse,
        rights_basis: file.rightsBasis,
        source_reference: file.sourceReference,
        license_id: file.licenseId,
        attribution: file.attribution,
      })),
    };
  }

  function persistDraftSnapshot(draft) {
    try {
      const validationError = validateDraftSnapshot(draft);
      if (validationError) throw new Error(validationError);
      const serialized = JSON.stringify(draft);
      const roundTripDraft = JSON.parse(serialized);
      const roundTripError = validateDraftSnapshot(roundTripDraft);
      if (roundTripError) throw new Error(`Snapshot sau JSON serialize không hợp lệ: ${roundTripError}`);

      const previousRaw = localStorage.getItem(draftStorageKey);
      let writeStarted = false;
      try {
        localStorage.setItem(draftStorageKey, serialized);
        writeStarted = true;
        const storedRaw = localStorage.getItem(draftStorageKey);
        if (storedRaw !== serialized) throw new Error('Đọc lại snapshot sau khi ghi không khớp dữ liệu vừa lưu.');
        const storedDraft = JSON.parse(storedRaw);
        const storedError = validateDraftSnapshot(storedDraft);
        if (storedError) throw new Error(`Snapshot đọc lại không hợp lệ: ${storedError}`);
        savedDraft = storedDraft;
      } catch (error) {
        if (writeStarted) {
          try {
            if (previousRaw === null) localStorage.removeItem(draftStorageKey);
            else localStorage.setItem(draftStorageKey, previousRaw);
          } catch (restoreError) {
            throw new Error(`${error.message} Không khôi phục được snapshot cũ: ${restoreError.message}`);
          }
        }
        throw error;
      }

      draftAvailable = true;
      invalidDraftMessage = '';
      draftDirty = false;
      const timeLabel = new Date(savedDraft.saved_at).toLocaleTimeString();
      setDraftStatus(`Đã tự lưu ${files.length} ảnh vào trình duyệt lúc ${timeLabel}. Ảnh không được tải lên máy chủ.`, 'saved');
      updateDraftControls();
      return true;
    } catch (error) {
      draftDirty = true;
      setDraftStatus(`Không xác thực/ghi lại được bản nháp (${error.message}). Hãy xuất JSON batch; snapshot cũ được giữ nếu bộ nhớ cho phép.`, 'error');
      showToast('Không tự lưu được bản nháp. Hãy xuất JSON batch để tránh mất nhãn.');
      return false;
    }
  }

  function saveDraftWithCachedHashes() {
    if (!files.length || files.some((file) => !file.image?.naturalWidth || !file.sha256)) return false;
    const draft = createDraftSnapshot();
    draft.images.forEach((record, index) => { record.sha256 = files[index].sha256; });
    return persistDraftSnapshot(draft);
  }

  async function saveDraftNow() {
    if (!files.length || files.some((file) => !file.image?.naturalWidth)) return false;
    const revision = ++draftSaveRevision;
    const fileIds = files.map((file) => file.id);
    const draft = createDraftSnapshot();
    try {
      setDraftStatus('Đang tính SHA-256 và tự lưu bản nháp cục bộ…', 'info');
      for (let index = 0; index < files.length; index += 1) {
        draft.images[index].sha256 = await getFileSha256(files[index]);
      }
      if (revision !== draftSaveRevision
          || JSON.stringify(files.map((file) => file.id)) !== JSON.stringify(fileIds)) return false;
      return persistDraftSnapshot(draft);
    } catch (error) {
      if (revision !== draftSaveRevision) return false;
      draftDirty = true;
      setDraftStatus(`${error.message} Không thể tạo bản nháp có thể khôi phục an toàn; hãy xuất JSON batch. Bản nháp cũ không bị xóa.`, 'error');
      showToast('Không thể xác minh ảnh để tự lưu. Hãy xuất JSON batch.');
      return false;
    }
  }

  function scheduleDraftSave() {
    if (!files.length) return;
    draftDirty = true;
    draftSaveRevision += 1;
    if (restoreSelectionPending || draftRestoreInProgress) {
      setDraftStatus('Phiên thay đổi trong lúc khôi phục đang chờ. Thao tác khôi phục sẽ bị hủy để bảo toàn phiên hiện tại.', 'error');
      return;
    }
    preserveStoredDraftAfterRestoreFailure = false;
    if (draftSaveTimer !== null) window.clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
    if (files.some((file) => !file.image?.naturalWidth)) {
      setDraftStatus('Đang chờ ảnh tải xong trước khi tự lưu bản nháp.', 'info');
      return;
    }
    setDraftStatus('Đang tự lưu bản nháp cục bộ…', 'info');
    draftSaveTimer = window.setTimeout(() => {
      draftSaveTimer = null;
      void saveDraftNow();
    }, 180);
  }

  function cancelPendingDraftSave() {
    if (draftSaveTimer !== null) window.clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
    draftSaveRevision += 1;
    draftDirty = false;
  }

  function removeSavedDraft() {
    if (restoreSelectionPending || draftRestoreInProgress) return false;
    cancelPendingDraftSave();
    try {
      localStorage.removeItem(draftStorageKey);
      savedDraft = null;
      draftAvailable = false;
      invalidDraftMessage = '';
      updateDraftControls();
      if (files.length) {
        setDraftStatus('Đã xóa snapshot. Phiên hiện tại vẫn còn; thao tác sửa tiếp sẽ tạo bản nháp mới.', 'info');
      }
      return true;
    } catch (error) {
      if (files.length) scheduleDraftSave();
      setDraftStatus(files.length
        ? 'Không thể xóa bản nháp. Phiên đang mở vẫn được giữ và autosave đã được lên lịch lại.'
        : 'Không thể xóa bản nháp khỏi bộ nhớ trình duyệt.', 'error');
      showToast('Không xóa được bản nháp đã lưu.');
      return false;
    }
  }

  function loadImageFile(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => resolve({ file, url, image });
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error(`Không đọc được ảnh ${file.name}.`));
      };
      image.src = url;
    });
  }

  async function restoreDraftWithFiles(fileList) {
    if (!pendingRestoreDraft || !restoreSelectionPending || draftRestoreInProgress) return;
    const draft = pendingRestoreDraft;
    const restoreRevision = pendingRestoreRevision;
    const restoreHadUnsavedChanges = pendingRestoreHadUnsavedChanges;
    pendingRestoreDraft = null;
    pendingRestoreRevision = null;
    pendingRestoreHadUnsavedChanges = false;
    restoreSelectionPending = false;
    elements.restoreDraft.disabled = true;
    draftRestoreInProgress = true;
    setDraftStatus('Đang xác minh ảnh gốc để khôi phục bản nháp…', 'info');
    document.body.inert = true;
    let selected = [];
    const temporaryUrls = [];
    let restoreCommitted = false;
    try {
      selected = Array.from(fileList);
      if (restoreRevision !== draftSaveRevision) {
        throw new Error('Phiên đang mở thay đổi trong lúc hộp chọn ảnh chờ. Khôi phục đã bị hủy để bảo toàn phiên hiện tại.');
      }
      if (selected.length !== draft.images.length) {
        throw new Error(`Cần chọn đúng ${draft.images.length} ảnh của bản nháp; hiện đã chọn ${selected.length}. Không ảnh nào được gắn nhãn.`);
      }
      if (selected.length > maxSessionImages
          || selected.some((file) => !acceptedMimeTypes.has(file.type.toLowerCase()) || file.size > maxFileBytes)
          || selected.reduce((total, file) => total + file.size, 0) > maxSessionBytes) {
        throw new Error('Các ảnh chọn lại vượt giới hạn định dạng/dung lượng của phiên. Không ảnh nào được gắn nhãn.');
      }

      const loaded = [];
      for (const file of selected) {
        const asset = await loadImageFile(file);
        temporaryUrls.push(asset.url);
        loaded.push(asset);
      }
      const totalPixels = loaded.reduce((total, asset) => total + asset.image.naturalWidth * asset.image.naturalHeight, 0);
      if (loaded.some((asset) => asset.image.naturalWidth * asset.image.naturalHeight > maxImagePixels)
          || totalPixels > maxSessionPixels) {
        throw new Error('Các ảnh chọn lại vượt giới hạn pixel của phiên. Không ảnh nào được gắn nhãn.');
      }

      const assetsByKey = new Map();
      for (const asset of loaded) {
        asset.sha256 = await sha256Blob(asset.file);
        const key = draftImageKey(asset.file.name, asset.file.size, asset.image.naturalWidth,
          asset.image.naturalHeight, asset.sha256);
        if (assetsByKey.has(key)) throw new Error(`Ảnh ${asset.file.name} bị trùng thông tin nên không thể ghép duy nhất. Không ảnh nào được gắn nhãn.`);
        assetsByKey.set(key, asset);
      }

      const restoredFiles = draft.images.map((record) => {
        const key = draftImageKey(record.file_name, record.file_size, record.width, record.height, record.sha256);
        const asset = assetsByKey.get(key);
        if (!asset) throw new Error(`Không khớp ảnh gốc ${record.file_name} (${record.file_size} byte, ${record.width}×${record.height}). Không ảnh nào được gắn nhãn.`);
        assetsByKey.delete(key);
        const otherSceneNoDepictedPeopleReviewed = record.other_scene_no_depicted_people_reviewed === true;
        const legacyOtherSceneNeedsReview = record.scene_type === 'other'
          && !otherSceneNoDepictedPeopleReviewed;
        const annotations = record.annotations.map((annotation) => ({
          ...annotation,
          ...(legacyOtherSceneNeedsReview && isSourceDependentHeadClass(annotation.classKey)
            ? { reviewState: 'uncertain' } : {}),
        }));
        const frameSourceStatus = legacyOtherSceneNeedsReview ? 'review_required' : record.frame_source_status;
        const depictionSurfaces = record.depiction_surfaces.map((surface) => ({
          surfaceId: surface.surface_id,
          surfaceType: surface.surface_type,
        }));
        const restoredFile = {
          id: record.image_id.toLowerCase(),
          name: asset.file.name,
          url: asset.url,
          blob: asset.file,
          image: asset.image,
          sha256: asset.sha256,
          sha256Promise: null,
          annotations,
          imageReviewStatus: 'pending',
          frameSourceStatus,
          frameSourceReviewedAt: legacyOtherSceneNeedsReview ? null : record.frame_source_reviewed_at,
          groupId: record.group_id,
          sceneType: record.scene_type,
          otherSceneNoDepictedPeopleReviewed,
          depictionSurfaceTypes: [...record.depiction_surface_types],
          depictionSurfaceCounts: { ...record.depiction_surface_counts },
          depictionSurfaces,
          split: record.split,
          trainingUse: record.training_use,
          rightsBasis: record.rights_basis,
          sourceReference: record.source_reference,
          licenseId: record.license_id,
          attribution: record.attribution,
        };
        const sourceGateIssue = !restoredFile.sceneType
          || (restoredFile.sceneType === 'other' && !restoredFile.otherSceneNoDepictedPeopleReviewed)
          || hasContradictoryDepictionMetadata(restoredFile)
          || needsDepictionSurfaceType(restoredFile)
          || !!getDepictionRegionCoverageIssue(restoredFile);
        if (frameSourceStatus === 'clear' && sourceGateIssue) {
          restoredFile.frameSourceStatus = 'review_required';
          restoredFile.frameSourceReviewedAt = null;
          restoredFile.imageReviewStatus = annotations.length ? 'labels_need_review' : 'pending';
          annotations.forEach((annotation) => {
            if (isSourceDependentHeadClass(annotation.classKey)) annotation.reviewState = 'uncertain';
          });
        } else if (annotations.length) {
          restoredFile.imageReviewStatus = record.image_review_status === 'reviewed_labeled'
            && restoredFile.frameSourceStatus === 'clear'
            && annotations.every((annotation) => effectiveReviewState(annotation, restoredFile) !== 'uncertain')
            ? 'reviewed_labeled' : 'labels_need_review';
        } else {
          restoredFile.imageReviewStatus = record.image_review_status === 'reviewed_empty'
            && restoredFile.frameSourceStatus === 'clear' ? 'reviewed_empty' : 'pending';
        }
        return restoredFile;
      });
      if (assetsByKey.size) throw new Error('Có ảnh được chọn không thuộc bản nháp. Không ảnh nào được gắn nhãn.');
      if (restoreRevision !== draftSaveRevision) {
        throw new Error('Phiên đang mở thay đổi trong lúc xác minh ảnh. Khôi phục đã bị hủy để bảo toàn phiên hiện tại.');
      }

      files.forEach((file) => URL.revokeObjectURL(file.url));
      files.splice(0, files.length, ...restoredFiles);
      temporaryUrls.length = 0;
      restoreCommitted = true;
      draftDirty = false;
      const normalizedActiveId = draft.active_file_id.toLowerCase();
      activeFileId = restoredFiles.some((file) => file.id === normalizedActiveId)
        ? normalizedActiveId : restoredFiles[0]?.id ?? null;
      selectedBoxId = null;
      nextDepictionSurfaceId = '';
      zoom = 1;
      updateView();
      setDraftStatus(`Đã khôi phục an toàn ${restoredFiles.length} ảnh. Bản nháp vẫn được giữ cục bộ.`, 'saved');
      showToast(`Đã khôi phục ${restoredFiles.length} ảnh từ bản nháp.`);
    } catch (error) {
      temporaryUrls.forEach((url) => URL.revokeObjectURL(url));
      const hasUnstoredChanges = restoreHadUnsavedChanges || draftDirty;
      const unsavedNote = hasUnstoredChanges && files.length
        ? ' Phiên hiện tại còn thay đổi chưa lưu; hãy xuất JSON trước khi rời trang.' : '';
      setDraftStatus(`${error.message} Bản nháp đã lưu vẫn được giữ nguyên. Hãy chọn đúng ảnh gốc hoặc xuất JSON batch trước khi tiếp tục.${unsavedNote}`, 'error');
      showToast(error.message);
    } finally {
      draftRestoreInProgress = false;
      document.body.inert = false;
      if (!restoreCommitted && (restoreHadUnsavedChanges || draftDirty) && files.length) {
        draftDirty = true;
        preserveStoredDraftAfterRestoreFailure = true;
      }
      if (restoreCommitted) preserveStoredDraftAfterRestoreFailure = false;
      pendingRestoreDraft = null;
      pendingRestoreRevision = null;
      pendingRestoreHadUnsavedChanges = false;
      restoreSelectionPending = false;
      elements.restoreDraft.disabled = !!invalidDraftMessage;
      elements.restoreFileInput.value = '';
    }
  }

  function currentFile() {
    return files.find((file) => file.id === activeFileId) ?? null;
  }

  function needsDepictionSurfaceType(file) {
    return !!file && (depictionSceneTypes.has(file.sceneType)
      || file.annotations.some((annotation) => ['depicted_hat', 'depiction_region'].includes(annotation.classKey)))
      && file.depictionSurfaceTypes.length === 0;
  }

  function hasContradictoryDepictionMetadata(file) {
    return !!file && file.sceneType === 'other'
      && (file.depictionSurfaceTypes.length > 0
        || file.depictionSurfaces.length > 0
        || file.annotations.some((annotation) => ['depicted_hat', 'depiction_region'].includes(annotation.classKey)));
  }

  function updateDepictionSurfaceValidation(file = currentFile()) {
    const missing = needsDepictionSurfaceType(file);
    const contradictory = hasContradictoryDepictionMetadata(file);
    elements.depictionSurfaceError.hidden = !missing && !contradictory;
    elements.depictionSurfaceError.textContent = contradictory
      ? 'Cảnh có người trên bề mặt hiển thị phải là chỉ có nội dung hiển thị hoặc cảnh hỗn hợp, không chọn cảnh khác.'
      : 'Chọn ít nhất một loại bề mặt cho cảnh hoặc nhãn hình ảnh này trước khi rà nguồn và xuất.';
  }

  function buildDepictionSurfaces(surfaceTypes, counts, existingSurfaces = []) {
    const surfaces = [];
    depictionSurfaceTypeOrder.forEach((surfaceType) => {
      if (!surfaceTypes.includes(surfaceType)) return;
      const count = Math.max(1, Math.min(20, Number(counts[surfaceType]) || 1));
      const retainedSurfaces = existingSurfaces.filter((surface) => surface.surfaceType === surfaceType);
      for (let index = 1; index <= count; index += 1) {
        const surfaceId = retainedSurfaces[index - 1]?.surfaceId ?? 'surface:' + crypto.randomUUID();
        surfaces.push({ surfaceId, surfaceType });
      }
    });
    return surfaces;
  }

  function depictionSurfaceInstanceLabel(surface, surfaces) {
    const instancesOfType = surfaces.filter((item) => item.surfaceType === surface.surfaceType);
    const instanceIndex = instancesOfType.findIndex((item) => item.surfaceId === surface.surfaceId);
    const instanceNumber = instanceIndex >= 0 ? instanceIndex + 1 : 1;
    return depictionSurfaceLabels[surface.surfaceType] + ' ' + instanceNumber;
  }

  function getRegionWithInvalidSurfaceId(file) {
    const inventoryIds = new Set((file?.depictionSurfaces ?? []).map((surface) => surface.surfaceId));
    const seenIds = new Set();
    for (const region of file?.annotations.filter((annotation) => annotation.classKey === 'depiction_region') ?? []) {
      const surfaceId = region.depictionSurfaceId;
      if (!inventoryIds.has(surfaceId) || seenIds.has(surfaceId)) return region;
      seenIds.add(surfaceId);
    }
    return null;
  }

  function getMissingDepictionSurface(file) {
    const assignedIds = new Set((file?.annotations ?? [])
      .filter((annotation) => annotation.classKey === 'depiction_region')
      .map((annotation) => annotation.depictionSurfaceId));
    return (file?.depictionSurfaces ?? []).find((surface) => !assignedIds.has(surface.surfaceId)) ?? null;
  }

  function getDepictionRegionCoverageIssue(file) {
    if (!file) return '';
    const regions = file.annotations.filter((annotation) => annotation.classKey === 'depiction_region');
    const surfaces = file.depictionSurfaces ?? [];
    const requiresDepictionRegion = depictionSceneTypes.has(file.sceneType)
      || file.depictionSurfaceTypes.length > 0
      || regions.length > 0
      || file.annotations.some((annotation) => annotation.classKey === 'depicted_hat');
    if (surfaces.length === 0) {
      if (regions.length > 0) return 'Không thể có hộp vùng hiển thị khi inventory chưa khai báo bề mặt vật lý.';
      return requiresDepictionRegion ? 'Khai báo số bề mặt vật lý trước khi xác nhận nguồn.' : '';
    }

    const inventoryIds = new Set();
    for (const surface of surfaces) {
      if (!surface.surfaceId || !allowedDepictionSurfaceTypes.has(surface.surfaceType)) {
        return 'Inventory có bề mặt không hợp lệ; sửa lại loại và mã bề mặt.';
      }
      if (inventoryIds.has(surface.surfaceId)) {
        return 'Inventory có mã bề mặt trùng; mỗi bề mặt vật lý cần một mã riêng.';
      }
      inventoryIds.add(surface.surfaceId);
    }
    const invalidRegion = getRegionWithInvalidSurfaceId(file);
    if (invalidRegion) {
      return 'Có hộp vùng thiếu mã, trỏ tới bề mặt đã xóa hoặc dùng trùng mã. Chọn từng hộp và gán đúng bề mặt cụ thể.';
    }
    const regionCounts = new Map();
    regions.forEach((region) => {
      regionCounts.set(region.depictionSurfaceId, (regionCounts.get(region.depictionSurfaceId) ?? 0) + 1);
    });
    const missingSurface = surfaces.find((surface) => !regionCounts.has(surface.surfaceId));
    if (missingSurface) {
      return 'Vẽ một hộp riêng cho bề mặt còn thiếu: '
        + depictionSurfaceInstanceLabel(missingSurface, surfaces)
        + '. Nếu mất viền hoặc không rõ, giữ cần rà nguồn.';
    }
    const duplicatedSurface = surfaces.find((surface) => regionCounts.get(surface.surfaceId) !== 1);
    if (duplicatedSurface) {
      return 'Mỗi bề mặt vật lý chỉ được liên kết với đúng một hộp: '
        + depictionSurfaceInstanceLabel(duplicatedSurface, surfaces)
        + '.';
    }
    return '';
  }

  function updateDepictionRegionSurfaceControl(file = currentFile()) {
    const selectedAnnotation = file?.annotations.find((annotation) => annotation.id === selectedBoxId);
    const selectedRegion = selectedAnnotation?.classKey === 'depiction_region' ? selectedAnnotation : null;
    const surfaces = file?.depictionSurfaces ?? [];
    if (!surfaces.some((surface) => surface.surfaceId === nextDepictionSurfaceId)) nextDepictionSurfaceId = '';
    const missingSurface = getMissingDepictionSurface(file);
    if (!selectedRegion && !nextDepictionSurfaceId && missingSurface) {
      nextDepictionSurfaceId = missingSurface.surfaceId;
    }

    elements.depictionRegionSurfaceType.replaceChildren();
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = surfaces.length ? 'Chọn bề mặt cụ thể' : 'Khai báo inventory trước';
    elements.depictionRegionSurfaceType.append(placeholder);
    surfaces.forEach((surface) => {
      const option = document.createElement('option');
      option.value = surface.surfaceId;
      option.textContent = depictionSurfaceInstanceLabel(surface, surfaces);
      elements.depictionRegionSurfaceType.append(option);
    });

    elements.depictionRegionSurfaceGroup.hidden = !file
      || (activeClass !== 'depiction_region' && !selectedRegion);
    elements.depictionRegionSurfaceGroup.disabled = !file;
    elements.depictionRegionSurfaceType.value = selectedRegion
      ? (surfaces.some((surface) => surface.surfaceId === selectedRegion.depictionSurfaceId)
        ? selectedRegion.depictionSurfaceId : '')
      : nextDepictionSurfaceId;
    const issue = getDepictionRegionCoverageIssue(file);
    elements.depictionRegionSurfaceError.textContent = issue;
    elements.depictionRegionSurfaceError.hidden = !issue;
  }

  function saveDatasetMetadata() {
    const file = currentFile();
    if (!file) return;
    const nextSceneType = elements.imageSceneType.value;
    const nextSurfaceTypes = Array.from(new Set(elements.depictionSurfaceTypes
      .filter((input) => input.checked && allowedDepictionSurfaceTypes.has(input.value))
      .map((input) => input.value)));
    const nextSurfaceCounts = {};
    depictionSurfaceTypeOrder.forEach((surfaceType) => {
      if (!nextSurfaceTypes.includes(surfaceType)) {
        nextSurfaceCounts[surfaceType] = 0;
        return;
      }
      const countInput = elements.depictionSurfaceCountInputs.find((input) => input.dataset.surfaceType === surfaceType);
      const wasSelected = file.depictionSurfaceTypes.includes(surfaceType);
      const inputCount = Number(countInput?.value);
      const previousCount = Number(file.depictionSurfaceCounts?.[surfaceType]) || 1;
      nextSurfaceCounts[surfaceType] = wasSelected && Number.isInteger(inputCount)
        ? Math.max(1, Math.min(20, inputCount))
        : wasSelected ? Math.max(1, Math.min(20, previousCount)) : 1;
    });
    const nextSurfaces = buildDepictionSurfaces(nextSurfaceTypes, nextSurfaceCounts, file.depictionSurfaces);
    const sourceMetadataChanged = file.sceneType !== nextSceneType
      || JSON.stringify(file.depictionSurfaceTypes) !== JSON.stringify(nextSurfaceTypes)
      || JSON.stringify(file.depictionSurfaces) !== JSON.stringify(nextSurfaces);
    if (sourceMetadataChanged) {
      invalidateSourceReview(file);
      file.otherSceneNoDepictedPeopleReviewed = false;
    }
    file.groupId = elements.imageGroupId.value.trim();
    file.sceneType = nextSceneType;
    file.depictionSurfaceTypes = nextSurfaceTypes;
    file.depictionSurfaceCounts = nextSurfaceCounts;
    file.depictionSurfaces = nextSurfaces;
    file.split = elements.imageSplit.value;
    file.trainingUse = elements.imageTrainingUse.value;
    file.rightsBasis = elements.imageRightsBasis.value;
    file.sourceReference = elements.imageSourceReference.value.trim();
    file.licenseId = elements.imageLicenseId.value.trim();
    file.attribution = elements.imageAttribution.value.trim();
    updateDepictionSurfaceValidation(file);
    scheduleDraftSave();
  }

  function invalidateSourceReview(file) {
    file.frameSourceStatus = 'review_required';
    file.frameSourceReviewedAt = null;
    file.imageReviewStatus = file.annotations.length ? 'labels_need_review' : 'pending';
    if (file.sceneType === 'other') file.otherSceneNoDepictedPeopleReviewed = false;
    file.annotations.forEach((annotation) => {
      if (isSourceDependentHeadClass(annotation.classKey)) annotation.reviewState = 'uncertain';
    });
  }

  function deleteAnnotation(file, annotation) {
    const invalidatesSource = ['depiction_region', 'depicted_hat'].includes(annotation.classKey);
    file.annotations = file.annotations.filter((item) => item.id !== annotation.id);
    file.imageReviewStatus = file.annotations.length ? 'labels_need_review' : 'pending';
    if (invalidatesSource) invalidateSourceReview(file);
    if (selectedBoxId === annotation.id) selectedBoxId = null;
  }

  function resetImageReviewStatus(file) {
    file.imageReviewStatus = file.annotations.length ? 'labels_need_review' : 'pending';
  }

  function escaped(value) {
    const node = document.createElement('span');
    node.textContent = value;
    return node.innerHTML;
  }

  function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.add('is-visible');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => elements.toast.classList.remove('is-visible'), 2500);
  }

  function download(filename, content, mime) {
    const url = URL.createObjectURL(new Blob([content], { type: mime }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    window.setTimeout(() => {
      URL.revokeObjectURL(url);
      link.remove();
    }, 60_000);
  }

  function downloadBlob(filename, content) {
    const url = URL.createObjectURL(content);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    window.setTimeout(() => {
      URL.revokeObjectURL(url);
      link.remove();
    }, 60_000);
  }

  function overlayExportBlockReason(file) {
    if (!file?.image?.naturalWidth) return 'Chọn ảnh trước khi xuất PNG có khung.';
    if (!file.annotations.length) return 'Ảnh đang chọn không có hộp nhãn để xuất.';
    if (imageReviewStatusFor(file) !== 'reviewed_labeled') {
      return 'Hoàn tất rà toàn ảnh và xác nhận mọi hộp trước khi xuất PNG.';
    }
    if (hasContradictoryDepictionMetadata(file)) {
      return 'Sửa loại cảnh và bề mặt hiển thị trước khi xuất PNG.';
    }
    if (needsDepictionSurfaceType(file) || getDepictionRegionCoverageIssue(file)) {
      return 'Hoàn tất khai báo từng poster, ảnh in, màn hình và vùng tương ứng trước khi xuất PNG.';
    }
    return '';
  }

  function exportReviewedOverlay(file) {
    const width = file.image.naturalWidth;
    const height = file.image.naturalHeight;
    const footerHeight = Math.max(38, Math.round(Math.min(width, height) * 0.045));
    const output = document.createElement('canvas');
    output.width = width;
    output.height = height + footerHeight;
    const outputContext = output.getContext('2d');
    if (!outputContext) {
      showToast('Không tạo được ảnh PNG trên trình duyệt này.');
      return;
    }
    outputContext.drawImage(file.image, 0, 0, width, height);
    const lineWidth = Math.max(3, Math.round(Math.min(width, height) / 340));
    const fontSize = Math.max(10, Math.min(24, Math.round(Math.min(width, height) / 48)));
    const padding = Math.max(5, Math.round(fontSize * 0.4));
    outputContext.font = `600 ${fontSize}px "DM Sans", Arial, sans-serif`;
    outputContext.textBaseline = 'top';

    file.annotations.forEach((annotation) => {
      const category = byKey[annotation.classKey];
      if (!category) return;
      const x = annotation.x * width;
      const y = annotation.y * height;
      const boxWidth = annotation.width * width;
      const boxHeight = annotation.height * height;
      outputContext.save();
      outputContext.strokeStyle = '#fff';
      outputContext.lineWidth = lineWidth + 2;
      outputContext.strokeRect(x, y, boxWidth, boxHeight);
      outputContext.strokeStyle = category.color;
      outputContext.lineWidth = lineWidth;
      outputContext.fillStyle = `${category.color}18`;
      outputContext.fillRect(x, y, boxWidth, boxHeight);
      outputContext.strokeRect(x, y, boxWidth, boxHeight);

      const reviewState = effectiveReviewState(annotation, file);
      const suffix = category.key === 'hard_hat_worn' && reviewState === 'confirmed'
        ? ' · MỤC TIÊU'
        : reviewState === 'depicted' ? ' · TRONG HÌNH, KHÔNG TÍNH'
          : category.key === 'depiction_region' ? ' · VÙNG HIỂN THỊ' : ' · LOẠI TRỪ';
      const label = `${category.name}${suffix}`;
      const labelHeight = fontSize + padding * 2;
      const labelWidth = Math.min(width, outputContext.measureText(label).width + padding * 2);
      const labelX = Math.min(Math.max(0, x), width - labelWidth);
      const labelY = y >= labelHeight ? y - labelHeight : Math.min(height - labelHeight, y + boxHeight);
      outputContext.fillStyle = category.color;
      outputContext.fillRect(labelX, labelY, labelWidth, labelHeight);
      outputContext.fillStyle = '#fff';
      outputContext.fillText(label, labelX + padding, labelY + padding, Math.max(1, width - padding * 2));
      outputContext.restore();
    });

    outputContext.fillStyle = '#1d2d27';
    outputContext.fillRect(0, height, width, footerHeight);
    outputContext.fillStyle = '#fff';
    outputContext.font = `600 ${Math.max(10, Math.min(18, Math.round(width / 90)))}px "DM Sans", Arial, sans-serif`;
    outputContext.textBaseline = 'middle';
    outputContext.fillText(
      'BẢN XEM LẠI · KHÔNG PHẢI DỮ LIỆU HUẤN LUYỆN · CHƯA XÁC MINH NGUỒN/THẨM QUYỀN',
      padding,
      height + footerHeight / 2,
      Math.max(1, width - padding * 2),
    );

    output.toBlob((blob) => {
      if (!blob) {
        showToast('Không mã hóa được PNG rà soát.');
        return;
      }
      const stem = file.name.replace(/\.[^.]+$/u, '').replace(/[<>:"/\\|?*\u0000-\u001f]+/gu, '_');
      downloadBlob(`${stem}_REVIEW-ONLY.png`, blob);
      showToast('Đã tải PNG rà soát cục bộ. Ảnh chưa được duyệt để huấn luyện.');
    }, 'image/png');
  }

  function addLabelButtons(target, items) {
    target.innerHTML = items.map((item) => `
      <button class="label-choice" type="button" data-class="${item.key}" aria-pressed="false">
        <span class="swatch" style="--swatch:${item.color}" aria-hidden="true"></span>
        <span>${item.name}</span>
        <span class="class-count" data-count="${item.key}">0</span>
      </button>`).join('');
    target.querySelectorAll('.label-choice').forEach((button) => {
      button.addEventListener('click', () => {
        activeClass = button.dataset.class;
        selectedBoxId = null;
        updateView();
        if (activeClass === 'depiction_region') {
          elements.depictionRegionSurfaceType.focus({ preventScroll: true });
        } else {
          elements.canvas.focus({ preventScroll: true });
        }
      });
    });
  }

  async function addImages(fileList) {
    if (restoreSelectionPending || draftRestoreInProgress) {
      showToast('Đang khôi phục bản nháp. Hãy chờ thao tác này kết thúc rồi thêm ảnh.');
      elements.fileInput.value = '';
      return;
    }
    if (!files.length && draftAvailable) {
      showToast('Đang có bản nháp đã lưu. Hãy khôi phục hoặc xóa bản nháp trước khi bắt đầu batch mới.');
      elements.fileInput.value = '';
      return;
    }
    const candidates = [...fileList];
    const startingFileIds = files.map((file) => file.id);
    const seenNames = new Set(files.map((file) => file.name.toLowerCase()));
    let bytesRemaining = Math.max(0, maxSessionBytes - files.reduce((total, file) => total + file.blob.size, 0));
    let imageSlotsRemaining = Math.max(0, maxSessionImages - files.length);
    const images = [];
    for (const file of candidates) {
      if (!acceptedMimeTypes.has(file.type.toLowerCase()) || file.size > maxFileBytes
          || imageSlotsRemaining === 0 || file.size > bytesRemaining) continue;
      const nameKey = file.name.toLowerCase();
      if (seenNames.has(nameKey)) continue;
      seenNames.add(nameKey);
      images.push(file);
      bytesRemaining -= file.size;
      imageSlotsRemaining -= 1;
    }
    if (!images.length) {
      showToast('Chọn JPG, PNG hoặc WEBP. Tối đa 10 MiB mỗi ảnh, 50 MiB và 20 ảnh mỗi phiên.');
      elements.fileInput.value = '';
      return;
    }

    let existingHashes;
    let selectedHashes;
    pendingImageAddCount += 1;
    try {
      setDraftStatus('Đang kiểm tra SHA-256 của ảnh để tránh trùng nội dung…', 'info');
      existingHashes = new Set();
      for (const file of files) existingHashes.add(await getFileSha256(file));
      selectedHashes = [];
      for (const file of images) selectedHashes.push(await sha256Blob(file));
    } catch (error) {
      setDraftStatus(`${error.message} Không thêm batch mới; các ảnh và nhãn đang mở vẫn được giữ. Hãy xuất JSON batch trước khi tiếp tục.`, 'error');
      showToast('Không xác minh được ảnh bằng SHA-256. Phiên hiện tại được giữ; hãy xuất JSON.');
      elements.fileInput.value = '';
      return;
    } finally {
      pendingImageAddCount -= 1;
    }
    if (JSON.stringify(files.map((file) => file.id)) !== JSON.stringify(startingFileIds)) {
      setDraftStatus('Phiên ảnh đã thay đổi trong lúc kiểm tra fingerprint. Không thêm ảnh để tránh ghép sai; hãy chọn lại batch.', 'error');
      showToast('Phiên đã thay đổi trong lúc kiểm tra ảnh. Hãy chọn lại batch.');
      elements.fileInput.value = '';
      return;
    }

    const uniqueImages = [];
    const seenHashes = new Set(existingHashes);
    images.forEach((file, index) => {
      const digest = selectedHashes[index];
      if (seenHashes.has(digest)) return;
      seenHashes.add(digest);
      uniqueImages.push({ file, digest });
    });
    const rejectedCount = candidates.length - uniqueImages.length;
    if (!uniqueImages.length) {
      showToast('Các ảnh đã chọn trùng nội dung hoặc tên với ảnh trong phiên; không thêm ảnh trùng.');
      elements.fileInput.value = '';
      return;
    }

    const added = uniqueImages.map(({ file, digest }) => {
      const item = createFile(file);
      item.sha256 = digest;
      return item;
    });
    files.push(...added);
    if (!activeFileId) activeFileId = added[0].id;
    added.forEach((file) => {
      file.image = new Image();
      file.image.onload = () => {
        if (!files.includes(file)) {
          URL.revokeObjectURL(file.url);
          return;
        }
        const imagePixels = file.image.naturalWidth * file.image.naturalHeight;
        const loadedSessionPixels = files.reduce((total, candidate) => {
          if (candidate === file || !candidate.image?.naturalWidth) return total;
          return total + candidate.image.naturalWidth * candidate.image.naturalHeight;
        }, imagePixels);
        if (imagePixels > maxImagePixels || loadedSessionPixels > maxSessionPixels) {
          const index = files.indexOf(file);
          if (index !== -1) files.splice(index, 1);
          URL.revokeObjectURL(file.url);
          if (activeFileId === file.id) {
            activeFileId = files[0]?.id ?? null;
            nextDepictionSurfaceId = '';
          }
          showToast(imagePixels > maxImagePixels
            ? `Ảnh ${file.name} vượt giới hạn 24 megapixel.`
            : `Phiên làm việc vượt giới hạn tổng 48 megapixel. Đã bỏ ảnh ${file.name}.`);
        }
        updateView();
        scheduleDraftSave();
      };
      file.image.onerror = () => {
        const index = files.indexOf(file);
        if (index !== -1) files.splice(index, 1);
        URL.revokeObjectURL(file.url);
        if (activeFileId === file.id) {
          activeFileId = files[0]?.id ?? null;
          nextDepictionSurfaceId = '';
        }
        showToast(`Không đọc được ảnh ${file.name}.`);
        updateView();
        scheduleDraftSave();
      };
      file.image.src = file.url;
    });
    elements.fileInput.value = '';
    updateView();
    if (rejectedCount) showToast(`Đã bỏ qua ${rejectedCount} tệp. Mỗi ảnh tối đa 10 MiB; cả phiên tối đa 50 MiB và 20 ảnh.`);
  }

  function getCanvasLayout() {
    const file = currentFile();
    if (!file?.image?.naturalWidth) return null;
    const width = elements.canvas.clientWidth;
    const height = elements.canvas.clientHeight;
    const fit = Math.min(width / file.image.naturalWidth, height / file.image.naturalHeight);
    const scale = fit * zoom;
    const imageWidth = file.image.naturalWidth * scale;
    const imageHeight = file.image.naturalHeight * scale;
    return {
      x: (width - imageWidth) / 2,
      y: (height - imageHeight) / 2,
      width: imageWidth,
      height: imageHeight,
      canvasWidth: width,
      canvasHeight: height,
    };
  }

  function resizeCanvas() {
    const bounds = elements.canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    if (!bounds.width || !bounds.height) return;
    elements.canvas.width = Math.round(bounds.width * ratio);
    elements.canvas.height = Math.round(bounds.height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    drawCanvas();
  }

  function drawBox(annotation, layout, draft = false) {
    const item = byKey[annotation.classKey];
    const x = layout.x + annotation.x * layout.width;
    const y = layout.y + annotation.y * layout.height;
    const width = annotation.width * layout.width;
    const height = annotation.height * layout.height;
    context.save();
    // Keep small head boxes visible against varied warehouse and street scenes.
    const selected = annotation.id === selectedBoxId;
    context.strokeStyle = '#fff';
    context.lineWidth = selected ? 5 : 4;
    context.setLineDash(draft ? [5, 4] : []);
    context.strokeRect(x, y, width, height);
    context.strokeStyle = item.color;
    context.lineWidth = selected ? 3 : 2.5;
    context.setLineDash(draft ? [5, 4] : []);
    context.strokeRect(x, y, width, height);
    context.fillStyle = `${item.color}14`;
    context.fillRect(x, y, width, height);
    const label = item.name + (annotation.reviewState === 'uncertain' ? ' · Chưa xác định' : '');
    context.font = '600 11px "DM Sans", Arial, sans-serif';
    const labelWidth = context.measureText(label).width + 12;
    const labelTop = Math.max(layout.y, y - 23);
    context.fillStyle = item.color;
    context.fillRect(x, labelTop, labelWidth, 21);
    context.fillStyle = '#fff';
    context.fillText(label, x + 6, labelTop + 14);
    if (selected) {
      context.fillStyle = '#fff';
      context.strokeStyle = item.color;
      context.setLineDash([]);
      context.lineWidth = 2;
      for (const [handleX, handleY] of [[x, y], [x + width, y], [x, y + height], [x + width, y + height]]) {
        context.beginPath();
        context.arc(handleX, handleY, 3.3, 0, Math.PI * 2);
        context.fill();
        context.stroke();
      }
    }
    context.restore();
  }

  function drawCanvas() {
    const bounds = elements.canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, bounds.width, bounds.height);
    const file = currentFile();
    const layout = getCanvasLayout();
    if (!file?.image?.naturalWidth || !layout) return;
    context.drawImage(file.image, layout.x, layout.y, layout.width, layout.height);
    file.annotations.forEach((annotation) => drawBox(annotation, layout));
    if (dragAction?.mode === 'draw') {
      const left = Math.min(dragAction.start.x, dragAction.current.x);
      const top = Math.min(dragAction.start.y, dragAction.current.y);
      const right = Math.max(dragAction.start.x, dragAction.current.x);
      const bottom = Math.max(dragAction.start.y, dragAction.current.y);
      drawBox({ id: 'draft', classKey: activeClass, x: (left - layout.x) / layout.width,
        y: (top - layout.y) / layout.height, width: (right - left) / layout.width,
        height: (bottom - top) / layout.height }, layout, true);
    }
  }

  function wearerCount(file) {
    if (!file || file.frameSourceStatus !== 'clear') return 0;
    return file.annotations.filter((annotation) => {
      return isTargetWornClass(annotation.classKey) && effectiveReviewState(annotation, file) === 'confirmed';
    }).length;
  }

  function rectangleUnionArea(rectangles) {
    const valid = rectangles.filter((box) => box[2] > box[0] && box[3] > box[1]);
    const xEdges = [...new Set(valid.flatMap((box) => [box[0], box[2]]))].sort((a, b) => a - b);
    let total = 0;
    for (let index = 0; index < xEdges.length - 1; index += 1) {
      const left = xEdges[index];
      const right = xEdges[index + 1];
      if (right <= left) continue;
      const intervals = valid.filter((box) => box[0] < right && box[2] > left)
        .map((box) => [box[1], box[3]]).sort((a, b) => a[0] - b[0]);
      let coveredY = 0;
      if (intervals.length) {
        let [start, end] = intervals[0];
        for (const [nextStart, nextEnd] of intervals.slice(1)) {
          if (nextStart > end) {
            coveredY += end - start;
            [start, end] = [nextStart, nextEnd];
          } else {
            end = Math.max(end, nextEnd);
          }
        }
        coveredY += end - start;
      }
      total += (right - left) * coveredY;
    }
    return total;
  }

  function regionDisposition(annotation, file) {
    const regions = file.annotations.filter((item) => item.classKey === 'depiction_region');
    const box = [annotation.x, annotation.y,
      annotation.x + annotation.width, annotation.y + annotation.height];
    const boxArea = annotation.width * annotation.height;
    if (boxArea <= 0) return 'partial';
    const centerX = annotation.x + annotation.width / 2;
    const centerY = annotation.y + annotation.height / 2;
    const centerInside = regions.some((region) => centerX >= region.x
      && centerX <= region.x + region.width
      && centerY >= region.y && centerY <= region.y + region.height);
    const intersections = regions.map((region) => [
      Math.max(box[0], region.x), Math.max(box[1], region.y),
      Math.min(box[2], region.x + region.width), Math.min(box[3], region.y + region.height),
    ]);
    const coverage = rectangleUnionArea(intersections) / boxArea;
    if (centerInside || coverage >= 0.5) return 'depicted';
    return coverage > 0 ? 'partial' : 'clear';
  }

  function effectiveReviewState(annotation, file) {
    if (!isSourceDependentHeadClass(annotation.classKey)) {
      if (annotation.reviewState === 'uncertain') return 'uncertain';
      return 'confirmed';
    }
    if (file.sceneType === 'depiction_only') return 'depicted';
    if (!file.sceneType || (file.sceneType === 'other' && !file.otherSceneNoDepictedPeopleReviewed)) {
      return 'uncertain';
    }
    const disposition = regionDisposition(annotation, file);
    if (disposition === 'depicted') return 'depicted';
    if (disposition === 'partial') return 'uncertain';
    if (file.frameSourceStatus !== 'clear') return 'uncertain';
    if (annotation.reviewState === 'uncertain') return 'uncertain';
    if (annotation.reviewState === 'reviewed_confirmed') return 'confirmed';
    return 'uncertain';
  }

  function canConfirmAnnotation(annotation, file) {
    return !isSourceDependentHeadClass(annotation.classKey)
      || (file.sceneType && file.sceneType !== 'depiction_only'
        && (file.sceneType !== 'other' || file.otherSceneNoDepictedPeopleReviewed)
        && file.frameSourceStatus === 'clear' && regionDisposition(annotation, file) === 'clear');
  }

  function renderAssets() {
    elements.assetList.innerHTML = files.map((file, index) => {
      const selected = file.id === activeFileId;
      const imageReviewStatus = imageReviewStatusFor(file);
      const hasUncertainAnnotations = file.annotations.some(
        (annotation) => effectiveReviewState(annotation, file) === 'uncertain',
      );
      const imageReviewLabel = imageReviewStatus === 'reviewed_empty'
        ? 'Đã rà · không có nhãn'
        : imageReviewStatus === 'reviewed_labeled' && hasUncertainAnnotations
          ? 'Đã rà · còn hộp chưa rõ'
          : imageReviewStatus === 'reviewed_labeled' ? 'Đã rà nhãn'
          : imageReviewStatus === 'labels_need_review' ? 'Có nhãn cần rà' : 'Chưa rà ảnh';
      return `<button class="asset-item${selected ? ' is-selected' : ''}" type="button" data-file="${file.id}" aria-pressed="${selected}">
        <img class="asset-thumb" src="${file.url}" alt="">
        <span><span class="asset-name">${escaped(file.name)}</span><span class="asset-meta">${file.annotations.length} hộp · ${wearerCount(file)} mũ bảo hộ</span><span class="asset-meta">${imageReviewLabel}</span></span>
        <span class="asset-index">${String(index + 1).padStart(2, '0')}</span>
      </button>`;
    }).join('');
    elements.assetList.querySelectorAll('.asset-item').forEach((button) => {
      button.addEventListener('click', () => {
        activeFileId = button.dataset.file;
        selectedBoxId = null;
        nextDepictionSurfaceId = '';
        zoom = 1;
        updateView();
        scheduleDraftSave();
      });
    });
  }

  function renderAnnotations(file) {
    if (!file?.annotations.length) {
      elements.annotationList.innerHTML = '<div class="annotation-empty">Chưa có hộp nhãn. Chọn loại nhãn rồi kéo trên ảnh.</div>';
      return;
    }
    elements.annotationList.innerHTML = file.annotations.map((annotation, index) => {
      const category = byKey[annotation.classKey];
      const isWorn = isWornClass(annotation.classKey);
      const needsSourceReview = isSourceDependentHeadClass(annotation.classKey);
      const disposition = needsSourceReview ? regionDisposition(annotation, file) : 'clear';
      const reviewState = effectiveReviewState(annotation, file);
      const isCounted = isWorn && reviewState === 'confirmed';
      let status;
      if (needsSourceReview) {
        if (file.sceneType === 'depiction_only') status = 'Cảnh chỉ có nội dung hiển thị · không tính người thật';
        else if (!file.sceneType) status = 'Chọn loại cảnh trước khi xác nhận người thật';
        else if (file.sceneType === 'other' && !file.otherSceneNoDepictedPeopleReviewed) status = 'Cần rà toàn ảnh; chưa xác nhận không có người trong nội dung hiển thị';
        else if (disposition === 'depicted') status = 'Trong poster / ảnh / màn hình · không tính';
        else if (disposition === 'partial') status = 'Chồng lấn một phần · cần rà';
        else if (file.frameSourceStatus !== 'clear') status = 'Nguồn cảnh chưa xác minh · không tính';
        else if (reviewState === 'uncertain') status = 'Chưa xác định · cần rà';
        else if (isTargetWornClass(annotation.classKey)) status = 'Người thật đội mũ bảo hộ · được tính';
        else if (isWorn) status = 'Mũ ngoài mục tiêu · loại khỏi nhãn mô hình';
        else status = 'Người thật · đầu trần';
      } else {
        const regionSurface = annotation.classKey === 'depiction_region'
          ? file.depictionSurfaces.find((surface) => surface.surfaceId === annotation.depictionSurfaceId)
          : null;
        status = reviewState === 'uncertain' ? 'Chưa xác định · rà lại'
          : category.key === 'depiction_region'
            ? 'Vùng ' + (regionSurface ? depictionSurfaceInstanceLabel(regionSurface, file.depictionSurfaces) : 'chưa gắn bề mặt')
            : 'Không phải người đội';
      }
      const confirmBlocked = needsSourceReview
        && annotation.reviewState === 'uncertain' && !canConfirmAnnotation(annotation, file);
      const boxPosition = `x ${Math.round(annotation.x * 100)}%, y ${Math.round(annotation.y * 100)}%, rộng ${Math.round(annotation.width * 100)}%, cao ${Math.round(annotation.height * 100)}%`;
      const confirmHelp = !file.sceneType
        ? 'Chọn loại cảnh trước khi xác nhận nhãn đầu người'
        : file.sceneType === 'depiction_only'
          ? 'Cảnh chỉ có nội dung hiển thị không được tính là người thật'
          : file.sceneType === 'other' && !file.otherSceneNoDepictedPeopleReviewed
            ? 'Xác nhận đã rà toàn ảnh và không có người trên poster, ảnh in hoặc màn hình'
        : file.frameSourceStatus !== 'clear'
        ? 'Rà toàn cảnh trước khi xác nhận nguồn đầu người'
        : disposition !== 'clear' ? 'Hộp đầu người giao poster, ảnh hoặc màn hình không thể được xác nhận là người thật'
          : annotation.reviewState === 'uncertain' ? 'Xác nhận nhãn sau khi đã rà toàn cảnh'
            : 'Chọn để chuyển về cần rà lại';
      return `<div class="annotation-item${annotation.id === selectedBoxId ? ' is-selected' : ''}" data-annotation="${escaped(annotation.id)}" style="--swatch:${category.color}">
        <span class="annotation-dot" aria-hidden="true"></span>
        <span class="annotation-copy"><span class="annotation-name">${String(index + 1).padStart(2, '0')} · ${category.name}</span><span class="annotation-position">${status}</span><span class="visually-hidden">Vị trí ${boxPosition}.</span></span>
        <span class="annotation-controls"><button class="review-toggle${annotation.reviewState === 'uncertain' ? ' is-uncertain' : ''}" type="button" aria-label="${annotation.reviewState === 'uncertain' ? 'Đánh dấu đã xác định' : 'Đánh dấu chưa xác định'}" aria-pressed="${annotation.reviewState !== 'uncertain'}" title="${confirmHelp}"${confirmBlocked ? ' disabled' : ''}>?</button><button class="annotation-delete" type="button" aria-label="Xóa nhãn ${category.name}">×</button></span>
      </div>`;
    }).join('');
    elements.annotationList.querySelectorAll('.annotation-item').forEach((row) => {
      row.addEventListener('click', (event) => {
        const annotation = file.annotations.find((item) => item.id === row.dataset.annotation);
        if (!annotation) return;
        if (event.target.closest('.annotation-delete')) {
          deleteAnnotation(file, annotation);
        } else if (event.target.closest('.review-toggle')) {
          if (annotation.reviewState === 'uncertain' && !canConfirmAnnotation(annotation, file)) return;
          annotation.reviewState = annotation.reviewState === 'uncertain' ? 'reviewed_confirmed' : 'uncertain';
          resetImageReviewStatus(file);
        } else {
          selectedBoxId = annotation.id;
        }
        updateView();
        scheduleDraftSave();
      });
    });
  }

  function updateCounts(file) {
    for (const category of categories) {
      const count = file?.annotations.filter((item) => item.classKey === category.key).length ?? 0;
      const badge = document.querySelector(`[data-count="${category.key}"]`);
      if (badge) badge.textContent = count;
    }
  }

  function updateView() {
    const file = currentFile();
    const hasImage = !!file?.image?.naturalWidth;
    elements.assetCount.textContent = `${files.length} ảnh`;
    elements.reviewCount.textContent = files.length ? `${files.length} ẢNH TRONG PHIÊN` : 'CHƯA CÓ ẢNH';
    elements.emptyAssets.hidden = files.length > 0;
    elements.assetList.hidden = files.length === 0;
    elements.clearImages.disabled = files.length === 0;
    elements.exportJson.disabled = files.length === 0 || files.some((candidate) =>
      !candidate.image?.naturalWidth
      || ['pending', 'labels_need_review'].includes(imageReviewStatusFor(candidate)));
    const overlayExportBlocker = overlayExportBlockReason(file);
    elements.exportOverlay.disabled = !!overlayExportBlocker;
    elements.exportOverlay.title = overlayExportBlocker
      || 'Tải PNG rà soát cục bộ; trạng thái quyền được lấy từ metadata ảnh.';
    const projectPermissionStatus = file?.trainingUse === 'approved'
      && file.rightsBasis === 'permission' && file.sourceReference
      ? 'Quyền project được ghi theo khai báo người dùng; nguồn và thẩm quyền chưa xác minh độc lập.'
      : 'Quyền dùng ảnh chưa được ghi nhận.';
    const overlayExportStatus = overlayExportBlocker
      || `PNG chỉ dùng để xem lại. ${projectPermissionStatus}`;
    if (elements.exportOverlayStatus.textContent !== overlayExportStatus) {
      elements.exportOverlayStatus.textContent = overlayExportStatus;
    }
    elements.datasetMetadata.disabled = !hasImage;
    elements.imageReviewStatus.hidden = !hasImage;
    const imageReviewStatus = hasImage ? imageReviewStatusFor(file) : 'pending';
    const hasUncertainAnnotations = hasImage && file.annotations.some(
      (annotation) => effectiveReviewState(annotation, file) === 'uncertain',
    );
    elements.imageReviewStatusTitle.textContent = !hasImage ? 'Tiến độ rà ảnh'
      : imageReviewStatus === 'reviewed_empty'
        ? 'Đã rà ảnh · không có nhãn'
        : imageReviewStatus === 'reviewed_labeled' && hasUncertainAnnotations
          ? 'Đã rà ảnh · còn hộp chưa xác định'
          : imageReviewStatus === 'reviewed_labeled' ? 'Đã xác nhận rà hết ảnh và các nhãn'
          : imageReviewStatus === 'labels_need_review' ? 'Ảnh có nhãn cần rà' : 'Ảnh chưa rà';
    elements.markReviewedNoLabels.hidden = !hasImage || file.annotations.length > 0;
    elements.markReviewedNoLabels.disabled = !hasImage || file.annotations.length > 0
      || file.frameSourceStatus !== 'clear';
    elements.markReviewedNoLabels.title = elements.markReviewedNoLabels.disabled
      ? 'Rà toàn cảnh, chọn loại cảnh và xác minh nguồn ảnh trước.' : '';
    elements.markReviewedNoLabels.textContent = imageReviewStatus === 'reviewed_empty'
      ? 'Đặt lại: chưa rà ảnh'
      : 'Xác nhận đã rà: không có nhãn';
    elements.markReviewedNoLabels.setAttribute('aria-pressed', String(imageReviewStatus === 'reviewed_empty'));
    elements.markReviewedWithLabels.hidden = !hasImage || file.annotations.length === 0;
    const canCompleteLabels = hasImage && file.annotations.length > 0
      && file.frameSourceStatus === 'clear';
    elements.markReviewedWithLabels.disabled = !canCompleteLabels && imageReviewStatus !== 'reviewed_labeled';
    elements.markReviewedWithLabels.title = canCompleteLabels && hasUncertainAnnotations
      ? 'Hoàn tất lượt rà và giữ hộp chưa xác định trong JSON để đối chiếu; các hộp này không được chuyển vào dữ liệu huấn luyện.'
      : canCompleteLabels
        ? 'Xác nhận đã rà hết các đối tượng thuộc ontology trong toàn ảnh.'
      : !hasImage || file.frameSourceStatus !== 'clear'
        ? 'Rà toàn cảnh và xác minh nguồn ảnh trước.'
        : 'Rà lại ảnh và đánh dấu các nhãn đã xem.';
    elements.markReviewedWithLabels.textContent = imageReviewStatus === 'reviewed_labeled'
      ? 'Đặt lại: cần rà nhãn'
      : hasUncertainAnnotations
        ? 'Xác nhận đã rà · giữ nhãn chưa rõ'
        : 'Xác nhận đã rà hết nhãn trong ảnh';
    elements.markReviewedWithLabels.setAttribute('aria-pressed', String(imageReviewStatus === 'reviewed_labeled'));
    elements.canvas.hidden = !hasImage;
    elements.canvasEmpty.hidden = hasImage;
    elements.boxHelp.hidden = !hasImage;
    elements.dropZone.classList.toggle('has-image', hasImage);
    elements.canvasMode.textContent = hasImage ? 'Vẽ và rà soát hộp nhãn' : 'Chọn ảnh để bắt đầu';
    elements.zoomIn.disabled = !hasImage;
    elements.zoomOut.disabled = !hasImage;
    elements.deleteBox.disabled = !selectedBoxId;
    elements.zoomLevel.textContent = `${Math.round(zoom * 100)}%`;
    elements.imageDimensions.textContent = hasImage ? `${file.image.naturalWidth} × ${file.image.naturalHeight}px` : 'Chưa chọn ảnh';
    elements.imageGroupId.value = file?.groupId ?? '';
    elements.imageSceneType.value = file?.sceneType ?? '';
    elements.otherSceneReviewRow.hidden = !hasImage || file.sceneType !== 'other';
    elements.otherSceneReview.checked = file?.otherSceneNoDepictedPeopleReviewed ?? false;
    elements.otherSceneReview.disabled = !hasImage;
    const selectedSurfaceTypes = new Set(file?.depictionSurfaceTypes ?? []);
    elements.depictionSurfaceTypes.forEach((input) => {
      input.checked = selectedSurfaceTypes.has(input.value);
    });
    elements.depictionSurfaceCountInputs.forEach((input) => {
      const surfaceType = input.dataset.surfaceType;
      const selected = selectedSurfaceTypes.has(surfaceType);
      input.value = String(file?.depictionSurfaceCounts?.[surfaceType] ?? 0);
      input.min = selected ? '1' : '0';
      input.disabled = !hasImage || !selected;
    });
    updateDepictionSurfaceValidation(file);
    elements.imageSplit.value = file?.split ?? '';
    elements.imageTrainingUse.value = file?.trainingUse ?? 'unknown';
    elements.imageRightsBasis.value = file?.rightsBasis ?? '';
    elements.imageSourceReference.value = file?.sourceReference ?? '';
    elements.imageLicenseId.value = file?.licenseId ?? '';
    elements.imageAttribution.value = file?.attribution ?? '';
    updateDepictionRegionSurfaceControl(file);
    elements.boxCount.textContent = String(file?.annotations.length ?? 0);
    const annotations = file?.annotations ?? [];
    const suppressed = annotations.filter((item) => isSourceDependentHeadClass(item.classKey)
      && effectiveReviewState(item, file) === 'depicted').length;
    const uncertain = annotations.filter((item) => effectiveReviewState(item, file) === 'uncertain').length;
    elements.annotationTotal.textContent = `${annotations.length} hộp · ${wearerCount(file ?? { annotations: [] })} mũ bảo hộ · ${suppressed} hình · ${uncertain} cần rà`;
    const sceneClear = file?.frameSourceStatus === 'clear';
    elements.reviewScene.disabled = !hasImage;
    elements.reviewScene.textContent = sceneClear ? 'Đặt lại cần rà nguồn' : 'Xác nhận đã rà toàn cảnh';
    elements.reviewScene.setAttribute('aria-pressed', String(sceneClear));
    elements.sceneReviewTitle.textContent = sceneClear ? 'Đã xác minh nguồn ảnh' : 'Nguồn ảnh chưa xác minh';
    elements.sceneReviewStatus.textContent = sceneClear
      ? 'Giờ hãy xác nhận riêng từng hộp đầu/mũ người thật không giao vùng ảnh.'
      : file?.sceneType === 'depiction_only'
        ? 'Ảnh chỉ có nội dung hiển thị: mọi hộp đầu/mũ đều không được tính là người thật.'
        : file?.sceneType === 'other'
          ? 'Rà toàn ảnh gốc. Nếu có người trong poster, ảnh in hoặc màn hình, đổi sang cảnh hỗn hợp và khoanh từng bề mặt.'
          : 'Chọn loại cảnh, rà toàn ảnh và khoanh đủ poster, ảnh in, màn hình. Nếu còn mờ hoặc mất viền, giữ cần rà.';
    elements.wornLabels.querySelectorAll('.label-choice').forEach((button) => {
      const active = button.dataset.class === activeClass;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    elements.nonpersonLabels.querySelectorAll('.label-choice').forEach((button) => {
      const active = button.dataset.class === activeClass;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    renderAssets();
    renderAnnotations(file);
    updateCounts(file);
    requestAnimationFrame(resizeCanvas);
  }

  function imagePoint(event) {
    const layout = getCanvasLayout();
    if (!layout) return null;
    const bounds = elements.canvas.getBoundingClientRect();
    const x = event.clientX - bounds.left;
    const y = event.clientY - bounds.top;
    if (x < layout.x || y < layout.y || x > layout.x + layout.width || y > layout.y + layout.height) return null;
    return { x, y, nx: (x - layout.x) / layout.width, ny: (y - layout.y) / layout.height };
  }

  function hitBox(point, layout, file) {
    for (let index = file.annotations.length - 1; index >= 0; index -= 1) {
      const annotation = file.annotations[index];
      const left = layout.x + annotation.x * layout.width;
      const top = layout.y + annotation.y * layout.height;
      const right = left + annotation.width * layout.width;
      const bottom = top + annotation.height * layout.height;
      if (point.x >= left && point.x <= right && point.y >= top && point.y <= bottom) return annotation;
    }
    return null;
  }

  elements.canvas.addEventListener('pointerdown', (event) => {
    const file = currentFile();
    const point = imagePoint(event);
    const layout = getCanvasLayout();
    if (!file || !point || !layout) return;
    const found = event.shiftKey ? null : hitBox(point, layout, file);
    if (found) {
      selectedBoxId = found.id;
      dragAction = { mode: 'move', annotation: found, last: point, moved: false };
    } else {
      selectedBoxId = null;
      dragAction = { mode: 'draw', start: point, current: point };
    }
    elements.canvas.setPointerCapture(event.pointerId);
    updateView();
  });

  elements.canvas.addEventListener('pointermove', (event) => {
    if (!dragAction) return;
    const file = currentFile();
    const point = imagePoint(event);
    const layout = getCanvasLayout();
    if (!file || !point || !layout) return;
    if (dragAction.mode === 'draw') {
      dragAction.current = point;
    } else {
      if (!dragAction.moved) {
        dragAction.moved = true;
        resetImageReviewStatus(file);
        const movedClass = dragAction.annotation.classKey;
        if (isSourceDependentHeadClass(movedClass)) dragAction.annotation.reviewState = 'uncertain';
        if (['depiction_region', 'depicted_hat'].includes(movedClass)) invalidateSourceReview(file);
      }
      dragAction.annotation.x = Math.max(0, Math.min(1 - dragAction.annotation.width, dragAction.annotation.x + (point.nx - dragAction.last.nx)));
      dragAction.annotation.y = Math.max(0, Math.min(1 - dragAction.annotation.height, dragAction.annotation.y + (point.ny - dragAction.last.ny)));
      dragAction.last = point;
    }
    drawCanvas();
  });

  elements.canvas.addEventListener('pointerup', (event) => {
    if (!dragAction) return;
    const file = currentFile();
    const action = dragAction;
    dragAction = null;
    if (action.mode === 'draw' && file) {
      const last = imagePoint(event) ?? action.current;
      const left = Math.max(0, Math.min(action.start.nx, last.nx));
      const top = Math.max(0, Math.min(action.start.ny, last.ny));
      const right = Math.min(1, Math.max(action.start.nx, last.nx));
      const bottom = Math.min(1, Math.max(action.start.ny, last.ny));
      if (right - left >= 0.008 && bottom - top >= 0.008) {
        const regionSurfaceId = elements.depictionRegionSurfaceType.value;
        if (activeClass === 'depiction_region'
            && !file.depictionSurfaces.some((surface) => surface.surfaceId === regionSurfaceId)) {
          showToast('Chọn bề mặt vật lý trong inventory trước khi vẽ vùng này.');
          elements.depictionRegionSurfaceType.focus();
        } else {
          const annotation = { id: crypto.randomUUID(), classKey: activeClass, x: left, y: top,
            width: right - left, height: bottom - top,
            reviewState: isSourceDependentHeadClass(activeClass) ? 'uncertain' : 'confirmed' };
          if (activeClass === 'depiction_region') {
            annotation.depictionSurfaceId = regionSurfaceId;
            nextDepictionSurfaceId = '';
          }
          file.annotations.push(annotation);
          resetImageReviewStatus(file);
          if (['depiction_region', 'depicted_hat'].includes(annotation.classKey)) invalidateSourceReview(file);
          selectedBoxId = annotation.classKey === 'depiction_region' ? null : annotation.id;
          if (annotation.classKey === 'depiction_region') {
            nextDepictionSurfaceId = getMissingDepictionSurface(file)?.surfaceId ?? '';
          }
          const needsSourceReview = isSourceDependentHeadClass(annotation.classKey);
          const disposition = needsSourceReview ? regionDisposition(annotation, file) : 'clear';
          if (disposition === 'depicted') {
            showToast('Hộp trong poster, ảnh hoặc màn hình không được tính là người thật.');
          } else if (disposition === 'partial') {
            annotation.reviewState = 'uncertain';
            showToast('Hộp chồng lấn một phần với vùng hình ảnh. Đã chuyển sang chưa xác định để rà lại.');
          } else if (needsSourceReview) {
            showToast(isTargetWornClass(annotation.classKey)
              ? 'Hãy rà toàn cảnh và xác nhận nguồn trước khi tính mũ bảo hộ.'
              : isWornClass(annotation.classKey)
                ? 'Mũ này ngoài mục tiêu; converter sẽ loại nhãn và giữ ảnh làm nền âm.'
                : 'Hãy rà toàn cảnh và xác nhận đầu trần thuộc người thật.');
          }
        }
      }
    }
    if (elements.canvas.hasPointerCapture(event.pointerId)) elements.canvas.releasePointerCapture(event.pointerId);
    updateView();
    scheduleDraftSave();
  });

  elements.canvas.addEventListener('keydown', (event) => {
    if (event.key.toLowerCase() === 'u' && selectedBoxId) {
      event.preventDefault();
      const file = currentFile();
      const annotation = file?.annotations.find((item) => item.id === selectedBoxId);
      if (!annotation) return;
      if (annotation.reviewState === 'uncertain' && !canConfirmAnnotation(annotation, file)) {
        showToast(file.frameSourceStatus !== 'clear'
          ? 'Rà toàn cảnh và xác minh mọi poster, ảnh hoặc màn hình trước khi xác nhận.'
          : 'Hộp giao vùng ảnh không thể được xác nhận là người thật.');
        return;
      }
      annotation.reviewState = annotation.reviewState === 'uncertain' ? 'reviewed_confirmed' : 'uncertain';
      resetImageReviewStatus(file);
      updateView();
      scheduleDraftSave();
      showToast(annotation.reviewState === 'uncertain' ? 'Đã đánh dấu cần rà lại.' : 'Đã xác nhận nhãn sau khi rà lại.');
      return;
    }
    if ((event.key === 'Delete' || event.key === 'Backspace') && selectedBoxId) {
      event.preventDefault();
      const file = currentFile();
      const annotation = file?.annotations.find((item) => item.id === selectedBoxId);
      if (file && annotation) deleteAnnotation(file, annotation);
      updateView();
      scheduleDraftSave();
    }
  });

  elements.fileInput.addEventListener('change', (event) => addImages(event.target.files));
  elements.restoreDraft.addEventListener('click', () => {
    if (!savedDraft || invalidDraftMessage || restoreSelectionPending || draftRestoreInProgress) return;
    if (pendingImageAddCount || files.some((file) => !file.image?.naturalWidth)) {
      showToast('Đợi batch ảnh đang kiểm tra hoặc tải xong trước khi khôi phục.');
      return;
    }
    if (files.length && !window.confirm('Khôi phục sẽ thay thế phiên đang mở nếu ảnh được khớp đầy đủ. Hãy xuất JSON trước nếu cần giữ cả hai phiên. Tiếp tục chọn ảnh gốc?')) return;
    pendingRestoreDraft = savedDraft;
    pendingRestoreHadUnsavedChanges = draftDirty;
    restoreSelectionPending = true;
    cancelPendingDraftSave();
    pendingRestoreRevision = draftSaveRevision;
    if (pendingRestoreHadUnsavedChanges && files.length) {
      draftDirty = true;
      preserveStoredDraftAfterRestoreFailure = true;
    }
    elements.restoreDraft.disabled = true;
    elements.restoreFileInput.click();
  });
  elements.restoreFileInput.addEventListener('change', (event) => restoreDraftWithFiles(event.target.files));
  elements.restoreFileInput.addEventListener('cancel', () => {
    const hadUnsavedChanges = pendingRestoreHadUnsavedChanges || draftDirty;
    pendingRestoreDraft = null;
    pendingRestoreRevision = null;
    pendingRestoreHadUnsavedChanges = false;
    restoreSelectionPending = false;
    elements.restoreFileInput.value = '';
    elements.restoreDraft.disabled = !!invalidDraftMessage;
    if (hadUnsavedChanges && files.length) {
      draftDirty = true;
      preserveStoredDraftAfterRestoreFailure = true;
      setDraftStatus('Đã hủy khôi phục. Phiên đang mở còn thay đổi chưa lưu; bản nháp đã lưu được giữ nguyên. Hãy xuất JSON trước khi rời trang.', 'error');
    }
  });
  elements.discardDraft.addEventListener('click', () => {
    if (restoreSelectionPending || draftRestoreInProgress) {
      showToast('Hãy chờ thao tác khôi phục kết thúc trước khi xóa bản nháp.');
      return;
    }
    const message = files.length
      ? 'Xóa snapshot đã lưu? Phiên đang mở vẫn còn trên màn hình và sẽ không tự lưu lại ngay; thao tác sửa tiếp theo sẽ tạo snapshot mới. Không thể khôi phục snapshot cũ.'
      : 'Xóa bản nháp cục bộ đã lưu? Thao tác này không thể hoàn tác.';
    if (!draftAvailable || !window.confirm(message)) return;
    removeSavedDraft();
  });
  elements.addSmall.addEventListener('click', () => elements.fileInput.click());
  elements.dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    elements.dropZone.classList.add('is-over');
  });
  elements.dropZone.addEventListener('dragleave', (event) => {
    if (!elements.dropZone.contains(event.relatedTarget)) elements.dropZone.classList.remove('is-over');
  });
  elements.dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove('is-over');
    addImages(event.dataTransfer.files);
  });
  elements.clearImages.addEventListener('click', async () => {
    if (restoreSelectionPending || draftRestoreInProgress) {
      showToast('Hãy chờ thao tác khôi phục kết thúc trước khi xóa phiên.');
      return;
    }
    if (!files.length || !window.confirm('Lưu bản nháp cục bộ hiện tại rồi xóa ảnh khỏi phiên đang mở? Bản nháp sẽ vẫn còn để khôi phục; dùng nút “Xóa bản nháp đã lưu” nếu muốn xóa hẳn.')) return;
    cancelPendingDraftSave();
    const didSave = await saveDraftNow();
    if (!didSave) {
      showToast('Chưa thể lưu snapshot an toàn; phiên vẫn được giữ nguyên. Hãy thử lại hoặc xuất JSON batch.');
      return;
    }
    files.forEach((file) => URL.revokeObjectURL(file.url));
    files.length = 0;
    activeFileId = null;
    selectedBoxId = null;
    nextDepictionSurfaceId = '';
    zoom = 1;
    updateView();
    loadSavedDraft();
  });
  elements.reviewScene.addEventListener('click', () => {
    const file = currentFile();
    if (!file?.image?.naturalWidth) return;
    if (file.frameSourceStatus === 'clear') {
      invalidateSourceReview(file);
      showToast('Nguồn ảnh cần rà lại. Các hộp đầu/mũ người thật trở về chưa xác định.');
    } else {
      if (!file.sceneType) {
        showToast('Chọn loại cảnh trước khi xác nhận nguồn ảnh.');
        updateView();
        elements.imageSceneType.focus();
        return;
      }
      if (file.sceneType === 'other' && !file.otherSceneNoDepictedPeopleReviewed) {
        showToast('Cảnh khác cần xác nhận đã rà toàn ảnh và không có người trong poster, ảnh in hoặc màn hình.');
        elements.otherSceneReview.focus();
        return;
      }
      if (hasContradictoryDepictionMetadata(file)) {
        showToast('Đổi loại cảnh sang chỉ có nội dung hiển thị hoặc cảnh hỗn hợp.');
        updateView();
        elements.imageSceneType.focus();
        return;
      }
      if (needsDepictionSurfaceType(file)) {
        showToast('Chọn loại bề mặt cho cảnh hiển thị trước khi xác nhận nguồn.');
        updateView();
        elements.depictionSurfaceTypes[0]?.focus();
        return;
      }
      const regionCoverageIssue = getDepictionRegionCoverageIssue(file);
      if (regionCoverageIssue) {
        activeClass = 'depiction_region';
        const invalidRegion = getRegionWithInvalidSurfaceId(file);
        selectedBoxId = invalidRegion?.id ?? null;
        if (!invalidRegion) nextDepictionSurfaceId = getMissingDepictionSurface(file)?.surfaceId ?? '';
        updateView();
        elements.depictionRegionSurfaceType.focus();
        showToast(regionCoverageIssue);
        return;
      }
      file.frameSourceStatus = 'clear';
      file.frameSourceReviewedAt = new Date().toISOString();
      showToast('Đã xác minh toàn cảnh. Hãy rà và xác nhận riêng từng hộp đầu/mũ người thật.');
    }
    updateView();
    scheduleDraftSave();
  });
  elements.markReviewedNoLabels.addEventListener('click', () => {
    const file = currentFile();
    if (!file || file.annotations.length) return;
    if (file.frameSourceStatus !== 'clear') {
      showToast('Rà toàn cảnh và xác minh nguồn trước khi xác nhận ảnh không có nhãn.');
      return;
    }
    file.imageReviewStatus = file.imageReviewStatus === 'reviewed_empty' ? 'pending' : 'reviewed_empty';
    updateView();
    scheduleDraftSave();
  });
  elements.markReviewedWithLabels.addEventListener('click', () => {
    const file = currentFile();
    if (!file || !file.annotations.length) return;
    if (file.imageReviewStatus === 'reviewed_labeled'
        && file.frameSourceStatus === 'clear') {
      file.imageReviewStatus = 'labels_need_review';
    } else {
      if (file.frameSourceStatus !== 'clear') {
        showToast('Rà toàn cảnh và xác minh nguồn ảnh trước khi xác nhận hoàn tất nhãn.');
        return;
      }
      file.imageReviewStatus = 'reviewed_labeled';
    }
    updateView();
    scheduleDraftSave();
  });
  [elements.imageGroupId, elements.imageSourceReference, elements.imageLicenseId, elements.imageAttribution]
    .forEach((input) => input.addEventListener('input', saveDatasetMetadata));
  elements.imageSceneType.addEventListener('change', () => {
    saveDatasetMetadata();
    updateView();
  });
  elements.otherSceneReview.addEventListener('change', () => {
    const file = currentFile();
    if (!file) return;
    file.otherSceneNoDepictedPeopleReviewed = elements.otherSceneReview.checked;
    if (!file.otherSceneNoDepictedPeopleReviewed) invalidateSourceReview(file);
    updateView();
    scheduleDraftSave();
  });
  [elements.imageSplit, elements.imageTrainingUse, elements.imageRightsBasis]
    .forEach((input) => input.addEventListener('change', saveDatasetMetadata));
  elements.depictionSurfaceTypes.forEach((input) => input.addEventListener('change', () => {
    saveDatasetMetadata();
    updateView();
  }));
  elements.depictionSurfaceCountInputs.forEach((input) => input.addEventListener('change', () => {
    saveDatasetMetadata();
    updateView();
  }));
  elements.depictionRegionSurfaceType.addEventListener('change', () => {
    const file = currentFile();
    if (!file) return;
    const selectedRegion = file.annotations.find((annotation) => annotation.id === selectedBoxId
      && annotation.classKey === 'depiction_region');
    if (selectedRegion) {
      const nextSurfaceId = elements.depictionRegionSurfaceType.value;
      if (selectedRegion.depictionSurfaceId !== nextSurfaceId) {
        selectedRegion.depictionSurfaceId = nextSurfaceId;
        invalidateSourceReview(file);
      }
    } else {
      nextDepictionSurfaceId = elements.depictionRegionSurfaceType.value;
    }
    updateView();
    scheduleDraftSave();
  });
  elements.deleteBox.addEventListener('click', () => {
    const file = currentFile();
    if (!file || !selectedBoxId) return;
    const annotation = file.annotations.find((item) => item.id === selectedBoxId);
    if (annotation) deleteAnnotation(file, annotation);
    updateView();
    scheduleDraftSave();
  });
  elements.zoomIn.addEventListener('click', () => { zoom = Math.min(2, zoom + 0.1); updateView(); });
  elements.zoomOut.addEventListener('click', () => { zoom = Math.max(0.5, zoom - 0.1); updateView(); });
  elements.dismissNotice.addEventListener('click', () => elements.dismissNotice.closest('.notice').remove());
  elements.openGuide.addEventListener('click', () => elements.guideDialog.showModal());
  elements.closeGuide.addEventListener('click', () => elements.guideDialog.close());
  elements.guideDone.addEventListener('click', () => elements.guideDialog.close());
  elements.guideDialog.addEventListener('click', (event) => {
    if (event.target === elements.guideDialog) elements.guideDialog.close();
  });
  elements.exportJson.addEventListener('click', () => {
    if (!files.length || files.some((file) => !file.image?.naturalWidth)) {
      showToast('Đợi ảnh tải xong trước khi xuất JSON.');
      return;
    }
    const incompleteReviewFile = files.find((file) => {
      const status = imageReviewStatusFor(file);
      return status === 'pending' || status === 'labels_need_review';
    });
    if (incompleteReviewFile) {
      activeFileId = incompleteReviewFile.id;
      selectedBoxId = null;
      zoom = 1;
      updateView();
      showToast(`Chưa thể xuất JSON v7: ${incompleteReviewFile.name} chưa hoàn tất rà ảnh.`);
      return;
    }
    const contradictoryDepictionMetadata = files.find(hasContradictoryDepictionMetadata);
    if (contradictoryDepictionMetadata) {
      activeFileId = contradictoryDepictionMetadata.id;
      selectedBoxId = null;
      zoom = 1;
      updateView();
      scheduleDraftSave();
      elements.imageSceneType.focus();
      showToast('Sửa loại cảnh: không thể gắn bề mặt có người vào cảnh khác.');
      return;
    }
    const missingSurfaceTypes = files.find(needsDepictionSurfaceType);
    if (missingSurfaceTypes) {
      activeFileId = missingSurfaceTypes.id;
      selectedBoxId = null;
      zoom = 1;
      updateView();
      scheduleDraftSave();
      elements.depictionSurfaceTypes[0]?.focus();
      showToast('Chọn ít nhất một loại bề mặt cho cảnh hoặc nhãn hình ảnh trước khi xuất.');
      return;
    }
    const regionCoverageFile = files.find((file) => getDepictionRegionCoverageIssue(file));
    if (regionCoverageFile) {
      activeFileId = regionCoverageFile.id;
      const invalidRegion = getRegionWithInvalidSurfaceId(regionCoverageFile);
      selectedBoxId = invalidRegion?.id ?? null;
      if (!invalidRegion) nextDepictionSurfaceId = getMissingDepictionSurface(regionCoverageFile)?.surfaceId ?? '';
      activeClass = 'depiction_region';
      zoom = 1;
      updateView();
      scheduleDraftSave();
      elements.depictionRegionSurfaceType.focus();
      showToast(getDepictionRegionCoverageIssue(regionCoverageFile));
      return;
    }
    const dataset = {
      format: 'helmet-vision-review-v7',
      classes: categories.map(({ id, key }) => ({ id, name: key })),
      rule: 'Hardhat-only model review v7. Browser retains eight review classes, but only confirmed hard_hat_worn in a verified real scene is a target wearer and contributes to real_wearer_count; traffic helmets, caps, beanies, bare heads, depicted hats, and loose hats are not model targets. Every image starts with frame_source_status=review_required. Select a scene type before marking the source clear. For scene_type=other, explicitly confirm that a full-frame review found no people in posters, printed photos, or screens. Mark depiction_only head boxes as depicted and never count them as real wearers. For mixed_scene, mark every physical poster, printed photo, and screen that contains people. depiction_surface_types is a unique summary of the declared physical-surface inventory. Every depiction_region annotation binds to exactly one depiction_surface_id, and every inventory ID must have exactly one separate region before clear or export. If any surface is borderless or unclear, keep frame_source_status=review_required. depiction_only and mixed_scene require at least one physical surface. A worn-hat or bare_head box is suppressed if its center is inside any depiction_region or at least half its area is covered by the union of depiction regions. Smaller nonzero union coverage always remains uncertain. Only zero-overlap hard_hat_worn boxes with a clear frame, an eligible scene type, and explicit box confirmation can be exported as model target labels. Each image must be explicitly reviewed as empty or reviewed with labels before JSON v7 export.',
      images: files.map((file) => ({
        image_id: file.id,
        file_name: file.name,
        width: file.image.naturalWidth,
        height: file.image.naturalHeight,
        group_id: file.groupId,
        scene_type: file.sceneType,
        other_scene_no_depicted_people_reviewed: file.otherSceneNoDepictedPeopleReviewed,
        depiction_surface_types: Array.from(new Set(file.depictionSurfaces.map((surface) => surface.surfaceType))),
        depiction_surfaces: file.depictionSurfaces.map((surface) => ({
          surface_id: surface.surfaceId,
          surface_type: surface.surfaceType,
        })),
        split: file.split,
        rights: {
          training_use: file.trainingUse,
          basis: file.rightsBasis,
          source_reference: file.sourceReference,
          license_id: file.licenseId,
          attribution: file.attribution,
        },
        frame_source_status: file.frameSourceStatus,
        frame_source_reviewed_at: file.frameSourceReviewedAt,
        image_review_status: imageReviewStatusFor(file) === 'reviewed_labeled'
          ? 'reviewed_with_labels' : 'reviewed_empty',
        real_wearer_count: wearerCount(file),
        annotations: file.annotations.map(({ classKey, x, y, width, height, reviewState, depictionSurfaceId }) => ({
          class_id: byKey[classKey].id, class_name: classKey, x, y, width, height,
          ...(classKey === 'depiction_region' ? { depiction_surface_id: depictionSurfaceId } : {}),
          review_state: effectiveReviewState({ classKey, x, y, width, height, reviewState }, file),
          counts_as_real_wearer: isTargetWornClass(classKey)
            && effectiveReviewState({ classKey, x, y, width, height, reviewState }, file) === 'confirmed',
        })),
      })),
    };
    download('helmet-vision-review-v7.json', JSON.stringify(dataset, null, 2), 'application/json');
    const metadataIssueFiles = files.filter((file) => !file.groupId || !file.sceneType || !file.split
      || (file.sceneType === 'other' && !file.otherSceneNoDepictedPeopleReviewed)
      || file.trainingUse !== 'approved' || !file.rightsBasis
      || !file.sourceReference
      || (file.rightsBasis === 'license' && (!file.licenseId || !file.attribution)));
    const unreviewedSourceFiles = files.filter((file) => file.frameSourceStatus !== 'clear');
    const normalizeGroupIdForSplitCheck = (groupId) =>
      groupId.trim().replace(/[ßẞ]/g, 'ss').toUpperCase().toLowerCase();
    const splitByGroup = new Map();
    files.forEach((file) => {
      const groupId = file.groupId.trim();
      if (!groupId || !file.split) return;
      const key = normalizeGroupIdForSplitCheck(groupId);
      if (!splitByGroup.has(key)) splitByGroup.set(key, { splits: new Set(), spellings: new Set() });
      const group = splitByGroup.get(key);
      group.splits.add(file.split);
      group.spellings.add(groupId);
    });
    const conflictingGroups = new Set(
      [...splitByGroup]
        .filter(([, group]) => group.splits.size > 1 || group.spellings.size > 1)
        .map(([groupId]) => groupId),
    );
    const conflictingGroupFiles = files.filter((file) => {
      const groupId = file.groupId.trim();
      return groupId && conflictingGroups.has(normalizeGroupIdForSplitCheck(groupId));
    });
    const uncertainFiles = files.filter((file) =>
      file.annotations.some((annotation) => effectiveReviewState(annotation, file) === 'uncertain'));
    const filesNeedingReview = new Set([
      ...metadataIssueFiles,
      ...unreviewedSourceFiles,
      ...conflictingGroupFiles,
      ...uncertainFiles,
    ]);
    if (filesNeedingReview.size) {
      showToast('Đã xuất JSON v7. ' + filesNeedingReview.size + ' ảnh chưa đạt: '
        + metadataIssueFiles.length + ' thiếu metadata/quyền; '
        + unreviewedSourceFiles.length + ' chưa rà nguồn; '
        + conflictingGroupFiles.length + ' có thể trùng group_id theo chuẩn hóa gần đúng hoặc qua nhiều split; '
        + uncertainFiles.length + ' có hộp cần rà. Nhãn chưa xác định được giữ lại để đối chiếu nhưng converter sẽ chặn chúng khỏi dữ liệu huấn luyện. Các lý do có thể trùng ảnh; kiểm tra group_id của UI chỉ là cảnh báo gần đúng, converter mới thực hiện xác thực chính thức và sẽ chặn ID không hợp lệ.');
    } else {
      showToast('Đã xuất JSON v7 cùng trạng thái rà ảnh, metadata nguồn, split và quyền dùng ảnh.');
    }
  });
  elements.exportOverlay.addEventListener('click', () => {
    const file = currentFile();
    const blocker = overlayExportBlockReason(file);
    if (blocker) {
      showToast(blocker);
      return;
    }
    exportReviewedOverlay(file);
  });

  addLabelButtons(elements.wornLabels, categories.filter((item) => item.group === 'worn'));
  addLabelButtons(elements.nonpersonLabels, categories.filter((item) => item.group === 'depicted'));
  new ResizeObserver(resizeCanvas).observe(elements.dropZone);
  window.addEventListener('resize', resizeCanvas);
  window.addEventListener('beforeunload', (event) => {
    if (draftSaveTimer !== null) window.clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
    if (pendingImageAddCount > 0 || files.some((file) => !file.image?.naturalWidth)) {
      event.preventDefault();
      event.returnValue = '';
      if (draftDirty && files.length && !preserveStoredDraftAfterRestoreFailure
          && !restoreSelectionPending && !draftRestoreInProgress) scheduleDraftSave();
      setDraftStatus('Ảnh mới đang được kiểm tra hoặc tải. Hãy chờ hoàn tất trước khi rời trang.', 'error');
      return;
    }
    if (draftDirty && (preserveStoredDraftAfterRestoreFailure || restoreSelectionPending || draftRestoreInProgress)) {
      event.preventDefault();
      event.returnValue = '';
      setDraftStatus('Có thay đổi chưa lưu trong phiên hiện tại. Hãy ở lại để xuất JSON; bản nháp đã lưu được giữ nguyên.', 'error');
      return;
    }
    if (draftDirty && !saveDraftWithCachedHashes()) {
      event.preventDefault();
      event.returnValue = '';
      scheduleDraftSave();
      setDraftStatus('Bản nháp chưa được lưu đầy đủ. Hãy chờ autosave hoặc xuất JSON trước khi rời trang.', 'error');
    }
  });
  window.addEventListener('pagehide', (event) => {
    if (draftSaveTimer !== null) window.clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
    if (draftDirty && !preserveStoredDraftAfterRestoreFailure && !restoreSelectionPending && !draftRestoreInProgress) {
      saveDraftWithCachedHashes();
    }
    if (!event.persisted) files.forEach((file) => URL.revokeObjectURL(file.url));
  });
  loadSavedDraft();
  updateView();
})();
