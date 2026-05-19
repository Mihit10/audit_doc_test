import { getImageFromDB } from '../utils/indexedDB';

export async function submitPhotoAudit(photoEvidenceList: any[]) {
  try {
    const formData = new FormData();
    
    // Minimal standard metadata just so backend docxtpl has something
    formData.append('auditor_name', 'Test Auditor');
    formData.append('branch_name', 'Test Branch');
    
    // Clean up photo evidence for metadata
    const cleanedPhotosArray = photoEvidenceList.map((photo: any) => ({
      id: photo.id,
      title: photo.title,
      observation: photo.observation,
    }));
    
    formData.append('photo_metadata', JSON.stringify(cleanedPhotosArray));

    // Fetch Blobs from IndexedDB and append them
    for (let i = 0; i < photoEvidenceList.length; i++) {
      const photoItem = photoEvidenceList[i];
      for (let j = 0; j < photoItem.imageIds.length; j++) {
        const imageId = photoItem.imageIds[j];
        const blob = await getImageFromDB(imageId);
        if (blob) {
          formData.append('photo_files', blob, `obs_${photoItem.id}_img_${j}.jpg`);
        }
      }
    }

    const response = await fetch('/api/audits/add-and-generate', {
      method: 'POST',
      body: formData,
    });

    if (response.ok) {
      const data = await response.json();
      return { success: true, data };
    }

    const errorText = await response.text();
    throw new Error(`Server returned ${response.status}: ${errorText}`);
  } catch (error: any) {
    console.error('[API Submit Error]', error);
    return { success: false, message: error.message };
  }
}
