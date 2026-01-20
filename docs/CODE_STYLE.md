# Code Style Guide - Smart Motion Detector v2

## Genel Kurallar

### Line Endings
- **Unix-style (LF)** kullanılır (Windows CRLF değil)
- `.gitattributes` dosyası bunu otomatik normalize eder
- `.editorconfig` IDE'lerde otomatik ayarlanır

### Encoding
- **UTF-8** (BOM olmadan)

### Indentation
- **Python**: 4 spaces
- **JavaScript/TypeScript**: 2 spaces
- **JSON/YAML**: 2 spaces

---

## Python Style

### PEP 8 Uyumlu
```python
# Good
def calculate_distance(point_a: tuple, point_b: tuple) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((point_b[0] - point_a[0])**2 + (point_b[1] - point_a[1])**2)

# Bad
def calculateDistance(pointA,pointB):
    return math.sqrt((pointB[0]-pointA[0])**2+(pointB[1]-pointA[1])**2)
```

### Type Hints
```python
# Always use type hints
def process_frame(frame: np.ndarray, confidence: float = 0.5) -> list[dict]:
    """Process frame and return detections."""
    pass
```

### Docstrings
```python
def detect_person(frame: np.ndarray) -> list[dict]:
    """
    Detect persons in a frame using YOLOv8.
    
    Args:
        frame: Input frame as numpy array (BGR format)
        
    Returns:
        List of detection dictionaries with keys: bbox, confidence, class
        
    Raises:
        ValueError: If frame is empty or invalid
    """
    pass
```

### Imports
```python
# Standard library
import os
import sys
from pathlib import Path

# Third-party
import cv2
import numpy as np
from fastapi import FastAPI

# Local
from app.services.camera import CameraService
from app.models.config import Config
```

---

## TypeScript/React Style

### Functional Components
```typescript
// Good
interface Props {
  cameraId: string;
  onClose: () => void;
}

export const CameraCard: React.FC<Props> = ({ cameraId, onClose }) => {
  const [loading, setLoading] = useState(false);
  
  return (
    <div className="camera-card">
      {/* ... */}
    </div>
  );
};

// Bad
export function CameraCard(props) {
  return <div>{props.cameraId}</div>;
}
```

### Type Safety
```typescript
// Always define types
interface Camera {
  id: string;
  name: string;
  type: 'color' | 'thermal' | 'dual';
  enabled: boolean;
}

// Use enums for constants
enum CameraStatus {
  Connected = 'connected',
  Retrying = 'retrying',
  Down = 'down',
}
```

### Hooks
```typescript
// Custom hooks start with 'use'
export const useCamera = (cameraId: string) => {
  const [camera, setCamera] = useState<Camera | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchCamera(cameraId).then(setCamera).finally(() => setLoading(false));
  }, [cameraId]);
  
  return { camera, loading };
};
```

---

## File Naming

### Python
- **Modules**: `snake_case.py` (örn: `camera_service.py`)
- **Classes**: `PascalCase` (örn: `CameraService`)
- **Functions**: `snake_case` (örn: `get_camera_by_id`)
- **Constants**: `UPPER_SNAKE_CASE` (örn: `MAX_RETRY_COUNT`)

### TypeScript/React
- **Components**: `PascalCase.tsx` (örn: `CameraCard.tsx`)
- **Utilities**: `camelCase.ts` (örn: `apiClient.ts`)
- **Types**: `PascalCase` (örn: `Camera`, `CameraStatus`)
- **Hooks**: `camelCase` starting with `use` (örn: `useCamera`)

---

## Git Commit Messages

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: Yeni özellik
- `fix`: Bug fix
- `docs`: Dokümantasyon
- `style`: Formatting (kod davranışı değişmez)
- `refactor`: Code refactoring
- `test`: Test ekleme/düzeltme
- `chore`: Bakım işleri (build, deps)

### Examples
```bash
feat(camera): add RTSP connection retry logic

Implement exponential backoff for RTSP reconnection.
Max retry count: 5, base delay: 1s.

Closes #42

---

fix(ui): camera snapshot preview not showing

The snapshot was not being decoded properly from base64.
Added error handling and fallback image.

---

docs(api): update camera test endpoint examples

Added examples for thermal and dual camera types.
```

---

## Code Review Checklist

### Before PR
- [ ] Kod PEP 8 / ESLint kurallarına uygun
- [ ] Type hints / TypeScript types eklenmiş
- [ ] Docstrings / JSDoc comments eklenmiş
- [ ] Unit tests yazılmış (coverage > 70%)
- [ ] Linter hataları yok
- [ ] Commit messages düzgün formatlanmış
- [ ] Dokümantasyon güncellendi (gerekirse)

### Review Kriterleri
- Kod okunabilir mi?
- Edge case'ler handle edilmiş mi?
- Error handling yeterli mi?
- Performance sorunları var mı?
- Security açığı var mı?

---

## Linting & Formatting

### Python
```bash
# Black (formatter)
black app/ tests/

# isort (import sorting)
isort app/ tests/

# flake8 (linter)
flake8 app/ tests/

# mypy (type checker)
mypy app/
```

### TypeScript
```bash
# ESLint
npm run lint

# Prettier (formatter)
npm run format
```

---

## IDE Setup

### VS Code
Önerilen extensions:
- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- EditorConfig for VS Code
- Tailwind CSS IntelliSense

### Settings (`.vscode/settings.json`)
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.rulers": [120]
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

---

## Testing Standards

### Python
```python
# Use pytest
def test_camera_connection():
    """Test RTSP camera connection."""
    camera = CameraService("rtsp://test")
    assert camera.connect() == True
    
def test_camera_connection_failure():
    """Test RTSP connection failure handling."""
    camera = CameraService("rtsp://invalid")
    with pytest.raises(ConnectionError):
        camera.connect()
```

### TypeScript
```typescript
// Use Jest + React Testing Library
describe('CameraCard', () => {
  it('renders camera name', () => {
    render(<CameraCard camera={mockCamera} />);
    expect(screen.getByText('Gate')).toBeInTheDocument();
  });
  
  it('handles delete action', async () => {
    const onDelete = jest.fn();
    render(<CameraCard camera={mockCamera} onDelete={onDelete} />);
    
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    await waitFor(() => expect(onDelete).toHaveBeenCalled());
  });
});
```

---

## Performance Guidelines

### Python
- Async/await kullan (I/O operations için)
- Generator kullan (büyük listeler için)
- NumPy operations vectorize et
- Caching kullan (functools.lru_cache)

### React
- useMemo / useCallback kullan (gereksiz re-render önle)
- React.lazy kullan (code splitting)
- Virtual scrolling kullan (uzun listeler için)
- Debounce/throttle kullan (input events için)

---

## Security Best Practices

- Secrets asla commit etme (.env kullan)
- RTSP credentials loglarda gösterme
- Input validation her zaman yap
- SQL injection önle (SQLAlchemy ORM kullan)
- XSS önle (React otomatik escape eder)
- CORS ayarlarını production'da sıkılaştır

---

## Documentation

- Her public function/class dokümante et
- API endpoint'leri `API_CONTRACT.md`'de güncelle
- UI değişiklikleri `DESIGN_SYSTEM.md`'de güncelle
- Breaking changes `CHANGELOG.md`'de belirt
