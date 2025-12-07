# shadcn/ui Patterns

## Available UI Components (Pre-installed)

All components at `@/components/ui/*` - NO installation needed.

### Layout Components
- **Card**: Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent, CardFooter
- **Dialog**: Dialog, DialogTrigger, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription, DialogClose
- **Sheet**: Sheet, SheetTrigger, SheetContent, SheetHeader, SheetFooter, SheetTitle, SheetDescription, SheetClose
- **Drawer**: Drawer, DrawerTrigger, DrawerContent, DrawerHeader, DrawerFooter, DrawerTitle, DrawerDescription
- **Tabs**: Tabs, TabsList, TabsTrigger, TabsContent
- **Accordion**: Accordion, AccordionItem, AccordionTrigger, AccordionContent
- **Collapsible**: Collapsible, CollapsibleTrigger, CollapsibleContent

### Data Display
- **Table**: Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption
- **Empty**: Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyContent
- **Badge**: Badge (variants: default, secondary, destructive, outline)
- **Avatar**: Avatar, AvatarImage, AvatarFallback
- **Skeleton**: Skeleton
- **Progress**: Progress
- **Calendar**: Calendar
- **Chart**: Chart components for data visualization

### Form Components
- **Button**: Button (variants: default, destructive, outline, secondary, ghost, link; sizes: default, sm, lg, icon, icon-sm, icon-lg)
- **ButtonGroup**: ButtonGroup
- **Input**: Input
- **InputGroup**: InputGroup, InputGroupText
- **InputOTP**: InputOTP, InputOTPGroup, InputOTPSlot, InputOTPSeparator
- **Textarea**: Textarea
- **Select**: Select, SelectTrigger, SelectValue, SelectContent, SelectItem, SelectGroup, SelectLabel, SelectSeparator
- **Checkbox**: Checkbox
- **Switch**: Switch
- **RadioGroup**: RadioGroup, RadioGroupItem
- **Slider**: Slider
- **Label**: Label
- **Form** (react-hook-form): Form, FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage
- **Field**: Field, FieldGroup (alternative form layout)

### Navigation
- **NavigationMenu**: NavigationMenu, NavigationMenuList, NavigationMenuItem, NavigationMenuTrigger, NavigationMenuContent, NavigationMenuLink
- **DropdownMenu**: DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel, DropdownMenuGroup
- **ContextMenu**: ContextMenu, ContextMenuTrigger, ContextMenuContent, ContextMenuItem
- **Menubar**: Menubar, MenubarMenu, MenubarTrigger, MenubarContent, MenubarItem
- **Breadcrumb**: Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage
- **Pagination**: Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationPrevious, PaginationNext, PaginationEllipsis
- **Sidebar**: Sidebar, SidebarContent, SidebarHeader, SidebarFooter, SidebarMenu, SidebarMenuItem, SidebarMenuButton

### Overlay
- **Tooltip**: Tooltip, TooltipTrigger, TooltipContent, TooltipProvider
- **Popover**: Popover, PopoverTrigger, PopoverContent
- **HoverCard**: HoverCard, HoverCardTrigger, HoverCardContent
- **AlertDialog**: AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogFooter, AlertDialogTitle, AlertDialogDescription, AlertDialogAction, AlertDialogCancel
- **Command**: Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem, CommandSeparator

### Feedback
- **Alert**: Alert, AlertTitle, AlertDescription (variants: default, destructive)
- **Sonner**: Toaster, toast() function
- **Spinner**: Spinner

### Layout Utilities
- **AspectRatio**: AspectRatio
- **ScrollArea**: ScrollArea, ScrollBar
- **Separator**: Separator
- **Resizable**: ResizablePanelGroup, ResizablePanel, ResizableHandle
- **Toggle**: Toggle
- **ToggleGroup**: ToggleGroup, ToggleGroupItem
- **Kbd**: Kbd (keyboard shortcut display)

### Carousel (embla-carousel-react pre-installed)
- **Carousel**: Carousel, CarouselContent, CarouselItem, CarouselPrevious, CarouselNext

---

## Common Patterns

### Card Layout

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description text</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Content here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

### Dialog/Modal

```tsx
'use client';
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export function CreateDialog() {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create New</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Item</DialogTitle>
          <DialogDescription>Fill in the details below.</DialogDescription>
        </DialogHeader>
        <form onSubmit={() => setOpen(false)}>
          {/* form fields */}
        </form>
        <DialogFooter>
          <Button type="submit">Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### Empty State

```tsx
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription, EmptyContent } from '@/components/ui/empty';
import { Button } from '@/components/ui/button';
import { PackageOpen } from 'lucide-react';

function NoItemsFound() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <PackageOpen />
        </EmptyMedia>
        <EmptyTitle>No items found</EmptyTitle>
        <EmptyDescription>
          Get started by creating your first item.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button>Create Item</Button>
      </EmptyContent>
    </Empty>
  );
}
```

### Data Table

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

export function DataTable({ items = [] }: { items: Item[] }) {
  if (!items.length) return <NoItemsFound />;
  
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.id}>
            <TableCell>{item.name}</TableCell>
            <TableCell><Badge>{item.status}</Badge></TableCell>
            <TableCell className="text-right">
              <Button variant="ghost" size="sm">Edit</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Tabs

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

<Tabs defaultValue="tab1">
  <TabsList>
    <TabsTrigger value="tab1">Tab 1</TabsTrigger>
    <TabsTrigger value="tab2">Tab 2</TabsTrigger>
  </TabsList>
  <TabsContent value="tab1">Content 1</TabsContent>
  <TabsContent value="tab2">Content 2</TabsContent>
</Tabs>
```

### Select Dropdown

```tsx
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';

<Select onValueChange={setValue} defaultValue={value}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Select option" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="option1">Option 1</SelectItem>
    <SelectItem value="option2">Option 2</SelectItem>
  </SelectContent>
</Select>
```

### Carousel

```tsx
'use client';
import { Carousel, CarouselContent, CarouselItem, CarouselPrevious, CarouselNext } from '@/components/ui/carousel';

export function ImageCarousel({ items = [] }: { items: { id: string; image: string; title: string }[] }) {
  if (!items.length) return null;
  
  return (
    <Carousel className="w-full max-w-xl">
      <CarouselContent>
        {items.map((item) => (
          <CarouselItem key={item.id}>
            <img src={item.image} alt={item.title} className="w-full rounded-lg" />
          </CarouselItem>
        ))}
      </CarouselContent>
      <CarouselPrevious />
      <CarouselNext />
    </Carousel>
  );
}
```

### Alert / Error Display

```tsx
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Something went wrong. Please try again.</AlertDescription>
</Alert>
```

### Toast Notifications

```tsx
'use client';
import { toast } from 'sonner';

// Success
toast.success('Item created successfully');

// Error
toast.error('Failed to create item');

// With description
toast('Event created', {
  description: 'Your event has been scheduled.',
});
```

### Button Variants

```tsx
<Button>Default</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button size="icon"><Icon /></Button>
```

### Dropdown Menu

```tsx
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';

<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="icon">
      <MoreHorizontal />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem>Edit</DropdownMenuItem>
    <DropdownMenuItem>Duplicate</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

### Loading Skeleton

```tsx
import { Skeleton } from '@/components/ui/skeleton';

function LoadingCard() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-4 w-[200px]" />
        <Skeleton className="h-3 w-[150px]" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-20 w-full" />
      </CardContent>
    </Card>
  );
}
```
