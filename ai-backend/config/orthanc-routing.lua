-- Orthanc Lua script: route incoming studies to the AI segmentation service.
-- Triggered when a study has been stable (no new instances) for StableAge seconds.

function OnStableStudy(studyId, tags, metadata)
  PrintRecursive(tags)

  local study = ParseJson(RestApiGet('/studies/' .. studyId))
  local mainTags = study['MainDicomTags'] or {}
  local modality = mainTags['ModalitiesInStudy'] or ''
  local bodyPart = (mainTags['BodyPartExamined'] or ''):upper()
  local desc = (mainTags['StudyDescription'] or ''):upper()

  local pipeline = nil

  -- Neuro CTA detection
  if modality:find('CT') then
    if bodyPart:find('HEAD') or bodyPart:find('NECK')
       or desc:find('CTA') or desc:find('ANGIO') then
      pipeline = 'cta'
    end
  end

  -- Neuro MRI detection (Phase 2)
  if modality:find('MR') then
    if bodyPart:find('HEAD') or bodyPart:find('BRAIN') then
      pipeline = 'mri'
    end
  end

  if pipeline then
    print('Routing study ' .. studyId .. ' to pipeline: ' .. pipeline)
    local payload = DumpJson({
      study_id = studyId,
      pipeline = pipeline,
      modality = modality,
      body_part = bodyPart,
      description = desc
    })
    HttpPost('http://ai-service:8000/webhook/orthanc', payload)
  end
end
