# AI Agents Section Component

Component hiển thị danh sách AI agents với hiệu ứng glassmorphism và màu tím chủ đạo.

## 📍 Vị trí

- **File component**: `frontend/src/components/landing/ai-agents-section.tsx`
- **Đã tích hợp vào**: `frontend/src/routes/index.tsx` (Landing page)
- **Vị trí trong page**: Sau BentoSection, trước LargeTestimonial

## 🎨 Thiết kế

### Glassmorphism Effect
- Background semi-transparent với blur effect
- Border gradient màu tím
- Backdrop filter blur (12px cho card, 20px cho modal)
- Gradient overlay từ purple-500 đến transparent

### Màu sắc chủ đạo
- **Primary**: Purple/Violet tones
- **Card background**: `rgba(139, 92, 246, 0.1)` với backdrop blur
- **Border**: `border-purple-500/30` với hover effect
- **Text**: Purple-300 cho labels, foreground cho content

### Animations
- Hover effect: Scale 1.05 và translate Y -5px
- Background blobs: Animated scale và opacity
- Modal: Spring animation với scale và fade
- Floating icon: Bounce animation
- Skills list: Stagger animation khi modal mở
- **Staggered Layout**: Cards ở vị trí chẵn (index 1, 3) được đẩy lên 50px trên desktop (lg breakpoint+)

## 🖼️ Hình ảnh Agents

Component sử dụng các hình ảnh từ thư mục:
```
frontend/public/assets/images/agent/
├── develop.png
├── product owner.png
├── scrum master.png
└── tester.png
```

## 📦 Cấu trúc Component

### AIAgentsSection (Main Component)
- Hiển thị grid layout của các agent cards
- Quản lý state cho modal chi tiết
- Responsive: 1 col (mobile) → 2 cols (sm) → 3 cols (lg) → 5 cols (xl)

### AgentCard
- Card glassmorphism với hover effects
- Hiển thị ảnh agent trong container gradient
- Badge "CARD" màu tím
- Floating icon với animation
- Click để mở modal chi tiết

### AgentModal
- Modal glassmorphism với backdrop blur
- Hiển thị thông tin chi tiết agent:
  - Service badge (MetaGPT - Global Service)
  - Tên và role
  - Specialized expertise
  - Professional skills (danh sách với bullet points)
- Close button và click outside để đóng
- Animated skills list

## 🔧 Cấu hình Agents

Dữ liệu agents được định nghĩa trong file component:

```typescript
interface Agent {
    id: string;
    name: string;
    role: string;
    image: string;
    description: string;
    expertise: string;
    skills: string[];
    service: string;
}
```

Hiện tại có 5 agents:
1. **Mike** - Team Leader (Scrum Master)
2. **Emma** - Product Manager (Product Owner)
3. **Bob** - Architect (Developer)
4. **Alex** - Engineer (Tester)
5. **David** - Data Analyst (Developer)

## 🎯 Tính năng

### Card Features
- ✅ Glassmorphism effect với backdrop blur
- ✅ Purple theme với gradient borders
- ✅ Hover animations (scale + translate)
- ✅ Floating animated icon
- ✅ Badge "CARD" styling
- ✅ Responsive image container

### Modal Features
- ✅ Full glassmorphism modal
- ✅ Spring animation khi mở/đóng
- ✅ Click outside để đóng
- ✅ Close button với hover effect
- ✅ Rotating service icon
- ✅ Stagger animation cho skills list
- ✅ Close hint ở dưới modal
- ✅ **Watermark agent image**: Hình ảnh agent mờ (opacity 0.12) ở góc phải dưới làm background

### Section Features
- ✅ Animated background blobs
- ✅ Section header với badge
- ✅ Responsive grid layout
- ✅ Stagger animation cho cards khi scroll vào view
- ✅ **Staggered card layout**: Cards ở vị trí chẵn nhô lên 50px (chỉ trên desktop lg+)
- ✅ Purple gradient background

## 🚀 Sử dụng

Component đã được tích hợp vào landing page. Để sử dụng ở nơi khác:

```tsx
import { AIAgentsSection } from '@/components/landing/ai-agents-section';

function MyPage() {
  return (
    <div>
      <AIAgentsSection />
    </div>
  );
}
```

## 🎨 Customization

### Thay đổi màu sắc
Tìm và thay thế các class Tailwind:
- `purple-500` → màu chính mới
- `purple-300` → màu text/label mới
- `purple-950` → màu background tối mới

### Thêm/Sửa agents
Chỉnh sửa mảng `agents` trong file component:

```typescript
const agents: Agent[] = [
    {
        id: 'new-agent',
        name: 'Agent Name',
        role: 'Agent Role',
        image: '/assets/images/agent/your-image.png',
        description: 'Short description',
        expertise: 'Expertise area',
        skills: ['Skill 1', 'Skill 2', 'Skill 3'],
        service: 'Service Name'
    },
    // ... more agents
];
```

### Thay đổi layout
Chỉnh sửa grid classes trong AIAgentsSection:
```tsx
className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6"
```

## 📱 Responsive Breakpoints

- **Mobile** (< 640px): 1 column
- **Small** (≥ 640px): 2 columns
- **Large** (≥ 1024px): 3 columns
- **Extra Large** (≥ 1280px): 5 columns

## 🔗 Dependencies

- `framer-motion`: Animations
- `lucide-react`: Icons (X, Sparkles)
- `tailwindcss`: Styling
- Theme provider: Tương thích với dark/light mode

## 💡 Tips

1. **Performance**: Component sử dụng AnimatePresence để tối ưu animation khi mount/unmount modal
2. **Accessibility**: Thêm keyboard navigation cho modal (ESC để đóng)
3. **Images**: Đảm bảo tất cả ảnh agents có cùng kích thước và format để hiển thị đồng nhất
4. **Theme**: Component tự động adapt với dark/light theme thông qua Tailwind classes

## 🐛 Troubleshooting

### Modal không hiển thị
- Kiểm tra z-index của modal (hiện tại: z-50)
- Đảm bảo không có element nào có z-index cao hơn

### Ảnh không hiển thị
- Kiểm tra đường dẫn ảnh trong public folder
- Đảm bảo tên file khớp với path trong code

### Animation lag
- Giảm số lượng animated elements
- Sử dụng `will-change` CSS property cho các elements thường xuyên animate

## 🎨 Advanced Features

### 1. Staggered Card Layout

Cards được sắp xếp theo pattern "nhô lên" để tạo rhythm thị giác:

**Implementation:**
```tsx
className={`${index % 2 === 1 ? 'lg:mt-[-50px]' : ''}`}
```

**Behavior:**
- Cards ở vị trí **chẵn** (index 1, 3 - tức card thứ 2, 4): Được đẩy lên 50px
- Cards ở vị trí **lẻ** (index 0, 2, 4 - tức card thứ 1, 3, 5): Giữ nguyên baseline
- **Responsive**: Chỉ áp dụng từ breakpoint `lg` (1024px) trở lên
- Mobile và tablet: Cards xếp thẳng hàng bình thường

**Visual Effect:**
```
Desktop (lg+):     Mobile/Tablet:
  Card1              Card1
    Card2            Card2
  Card3              Card3
    Card4            Card4
  Card5              Card5
```

### 2. Watermark Agent Image trong Modal

Hình ảnh agent được hiển thị mờ ở góc phải dưới modal làm watermark:

**Implementation:**
```tsx
<div className="absolute bottom-0 right-0 w-64 h-64 pointer-events-none overflow-hidden rounded-3xl">
    <img
        src={agent.image}
        alt=""
        className="w-full h-full object-contain opacity-[0.12] blur-[2px]"
        style={{ transform: 'translate(20%, 20%) scale(1.2)' }}
    />
</div>
```

**Properties:**
- **Position**: Absolute ở góc phải dưới (bottom-right)
- **Size**: 256px x 256px (w-64 h-64)
- **Opacity**: 0.12 (12%) - rất mờ để không che khuất text
- **Blur**: 2px - tạo soft effect
- **Transform**:
  - `translate(20%, 20%)`: Đẩy ra ngoài một phần để tạo partial view
  - `scale(1.2)`: Phóng to 120% để tạo dramatic effect
- **Z-index**: Thấp hơn content (do không có z-index explicit)
- **Pointer Events**: None - không block interactions

**Visual Purpose:**
- Tạo depth và visual interest cho modal
- Reinforcement của agent identity
- Không ảnh hưởng đến readability của text
- Subtle branding element

## 📝 Notes

- Component được thiết kế theo design system của VibeSDLC
- Tương thích với theme provider hiện tại
- Sử dụng TypeScript để type safety
- Follow coding conventions của project
- **Staggered layout** tạo visual rhythm và modern aesthetic
- **Watermark image** thêm depth mà không làm mất focus vào content

