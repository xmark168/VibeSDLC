# Advanced Server Action Patterns

## Action with Redirect

```typescript
'use server';

import { prisma } from '@/lib/prisma';
import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const schema = z.object({
  title: z.string().min(1),
  content: z.string().min(10),
});

export async function createPost(formData: FormData) {
  const validated = schema.safeParse({
    title: formData.get('title'),
    content: formData.get('content'),
  });

  if (!validated.success) {
    return {
      success: false,
      fieldErrors: validated.error.flatten().fieldErrors,
    };
  }

  const post = await prisma.post.create({ data: validated.data });
  revalidatePath('/posts');
  redirect(`/posts/${post.id}`);
}
```

## Inline Action in Page

```tsx
// app/posts/[id]/page.tsx
import { prisma } from '@/lib/prisma';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PostPage({ params }: PageProps) {
  const { id } = await params;
  const post = await prisma.post.findUnique({ where: { id } });

  if (!post) redirect('/posts');

  async function deletePost() {
    'use server';
    await prisma.post.delete({ where: { id } });
    revalidatePath('/posts');
    redirect('/posts');
  }

  return (
    <div>
      <h1>{post.title}</h1>
      <form action={deletePost}>
        <button type="submit">Delete</button>
      </form>
    </div>
  );
}
```

## Full Form with useActionState

```tsx
'use client';

import { useActionState } from 'react';
import { createUser } from '@/app/actions/user';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function CreateUserForm() {
  const [state, formAction, isPending] = useActionState(createUser, null);

  return (
    <form action={formAction} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input id="name" name="name" required disabled={isPending} />
        {state?.fieldErrors?.name && (
          <p className="text-sm text-destructive">{state.fieldErrors.name[0]}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" required disabled={isPending} />
        {state?.fieldErrors?.email && (
          <p className="text-sm text-destructive">{state.fieldErrors.email[0]}</p>
        )}
      </div>

      <Button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create User'}
      </Button>

      {state?.success && <p className="text-green-600">Success!</p>}
      {state?.error && !state.fieldErrors && (
        <p className="text-destructive">{state.error}</p>
      )}
    </form>
  );
}
```

## Delete Button with Toast

```tsx
'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Trash2, Loader2 } from 'lucide-react';
import { deleteUser } from '@/app/actions/user';
import { toast } from 'sonner';

export function DeleteUserButton({ userId, userName }: { userId: string; userName: string }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleDelete = () => {
    if (!confirm(`Delete "${userName}"?`)) return;

    startTransition(async () => {
      const result = await deleteUser(userId);
      if (result.success) {
        toast.success('Deleted');
        router.refresh();
      } else {
        toast.error(result.error);
      }
    });
  };

  return (
    <Button variant="destructive" size="icon" onClick={handleDelete} disabled={isPending}>
      {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
    </Button>
  );
}
```
