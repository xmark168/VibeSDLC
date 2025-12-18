-- Seed Next.js Tech Stack
-- Run this SQL script directly in your database

-- Check if Next.js already exists
SELECT 
    id, code, name, is_active, created_at
FROM tech_stacks 
WHERE code = 'nextjs';

-- If not exists, insert Next.js tech stack
INSERT INTO tech_stacks (
    id,
    code,
    name,
    description,
    image,
    stack_config,
    is_active,
    display_order,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid(),  -- PostgreSQL function for UUID
    'nextjs',
    'Next.js',
    'Next.js 16 with React 19, TypeScript, Tailwind CSS, and Prisma',
    NULL,
    '{"runtime": "node", "package_manager": "pnpm", "framework": "nextjs", "version": "16", "language": "typescript", "styling": "tailwindcss", "database": "prisma", "testing": "jest"}'::jsonb,
    true,
    0,
    NOW(),
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM tech_stacks WHERE code = 'nextjs'
);

-- Verify insertion
SELECT 
    id, 
    code, 
    name, 
    description,
    stack_config,
    is_active,
    display_order,
    created_at,
    updated_at
FROM tech_stacks 
WHERE code = 'nextjs';

-- List all tech stacks
SELECT 
    code,
    name,
    is_active,
    display_order
FROM tech_stacks
ORDER BY display_order, name;
