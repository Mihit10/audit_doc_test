import React, { useState, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Camera, Image as ImageIcon, Trash2, Plus, X } from 'lucide-react';
import { saveImageToDB, getImageFromDB, deleteImageFromDB } from '../utils/indexedDB';

interface PhotoEvidenceItem {
  id: string;
  title: string;
  observation: string;
  imageIds: string[];
}

interface Props {
  value?: PhotoEvidenceItem[];
  onChange: (val: PhotoEvidenceItem[]) => void;
}

export const PhotoArrayInput: React.FC<Props> = ({ value = [], onChange }) => {
  const [items, setItems] = useState<PhotoEvidenceItem[]>(value.length > 0 ? value : [{ id: uuidv4(), title: '', observation: '', imageIds: [] }]);
  const [objectUrls, setObjectUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    // Load object URLs for all image IDs
    const loadImages = async () => {
      const urls: Record<string, string> = {};
      for (const item of items) {
        for (const imgId of item.imageIds) {
          if (!objectUrls[imgId]) {
            const blob = await getImageFromDB(imgId);
            if (blob) {
              urls[imgId] = URL.createObjectURL(blob);
            }
          }
        }
      }
      if (Object.keys(urls).length > 0) {
        setObjectUrls(prev => ({ ...prev, ...urls }));
      }
    };
    loadImages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  const updateItem = (id: string, field: keyof PhotoEvidenceItem, val: any) => {
    const newItems = items.map(item => item.id === id ? { ...item, [field]: val } : item);
    setItems(newItems);
    onChange(newItems);
  };

  const addItem = () => {
    const newItems = [...items, { id: uuidv4(), title: '', observation: '', imageIds: [] }];
    setItems(newItems);
    onChange(newItems);
  };

  const removeItem = (id: string) => {
    const itemToRemove = items.find(i => i.id === id);
    if (itemToRemove) {
      itemToRemove.imageIds.forEach(imgId => deleteImageFromDB(imgId));
    }
    const newItems = items.filter(i => i.id !== id);
    setItems(newItems);
    onChange(newItems);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>, itemId: string) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const currentItem = items.find(i => i.id === itemId);
    if (!currentItem) return;

    const newImageIds = [...currentItem.imageIds];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const imgId = uuidv4();
      await saveImageToDB(imgId, file);
      newImageIds.push(imgId);
      
      setObjectUrls(prev => ({
        ...prev,
        [imgId]: URL.createObjectURL(file)
      }));
    }

    updateItem(itemId, 'imageIds', newImageIds);
    // Clear input
    e.target.value = '';
  };

  const removeImage = (itemId: string, imgIdToRemove: string) => {
    const currentItem = items.find(i => i.id === itemId);
    if (!currentItem) return;

    deleteImageFromDB(imgIdToRemove);
    const newImageIds = currentItem.imageIds.filter(id => id !== imgIdToRemove);
    updateItem(itemId, 'imageIds', newImageIds);
    
    // Revoke object URL to prevent memory leaks
    if (objectUrls[imgIdToRemove]) {
      URL.revokeObjectURL(objectUrls[imgIdToRemove]);
      const newUrls = { ...objectUrls };
      delete newUrls[imgIdToRemove];
      setObjectUrls(newUrls);
    }
  };

  const FileInputRef = ({ itemId, capture }: { itemId: string, capture?: boolean }) => {
    const inputRef = useRef<HTMLInputElement>(null);
    return (
      <>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture={capture ? "environment" : undefined}
          multiple={!capture}
          style={{ display: 'none' }}
          onChange={(e) => handleFileSelect(e, itemId)}
        />
        <button 
          onClick={() => inputRef.current?.click()}
          style={{ 
            display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', 
            background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '4px', cursor: 'pointer', color: 'var(--text-h)'
          }}
        >
          {capture ? <Camera size={16} /> : <ImageIcon size={16} />}
          {capture ? 'Take Photo' : 'Upload Image'}
        </button>
      </>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {items.map((item, index) => (
        <div key={item.id} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', background: 'var(--code-bg)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h4 style={{ margin: 0, color: 'var(--text-h)' }}>Observation #{index + 1}</h4>
            {items.length > 1 && (
              <button onClick={() => removeItem(item.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>
                <Trash2 size={18} />
              </button>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', color: 'var(--text)' }}>Location / Title</label>
              <input
                type="text"
                value={item.title}
                onChange={e => updateItem(item.id, 'title', e.target.value)}
                placeholder="e.g. UPS Room, Main Panel"
                style={{ width: '100%', padding: '8px', border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg)', color: 'var(--text-h)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', color: 'var(--text)' }}>Observation Details</label>
              <textarea
                value={item.observation}
                onChange={e => updateItem(item.id, 'observation', e.target.value)}
                placeholder="Describe what was observed..."
                rows={3}
                style={{ width: '100%', padding: '8px', border: '1px solid var(--border)', borderRadius: '4px', background: 'var(--bg)', color: 'var(--text-h)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '8px', color: 'var(--text)' }}>Photos ({item.imageIds.length})</label>
              
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px' }}>
                {item.imageIds.map(imgId => (
                  <div key={imgId} style={{ position: 'relative', width: '100px', height: '100px', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                    {objectUrls[imgId] ? (
                      <img src={objectUrls[imgId]} alt="Evidence" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <div style={{ width: '100%', height: '100%', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>...</div>
                    )}
                    <button 
                      onClick={() => removeImage(item.id, imgId)}
                      style={{ position: 'absolute', top: '4px', right: '4px', background: 'rgba(0,0,0,0.5)', color: 'white', border: 'none', borderRadius: '50%', padding: '4px', cursor: 'pointer', display: 'flex' }}
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <FileInputRef itemId={item.id} capture={true} />
                <FileInputRef itemId={item.id} capture={false} />
              </div>
            </div>
          </div>
        </div>
      ))}

      <button 
        onClick={addItem}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', border: '1px dashed var(--border)', borderRadius: '8px', background: 'var(--code-bg)', color: 'var(--accent)', cursor: 'pointer', fontWeight: '500' }}
      >
        <Plus size={18} /> Add Another Observation
      </button>
    </div>
  );
};
