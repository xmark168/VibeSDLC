"""Seed TechStack data into database."""

import logging

from sqlmodel import Session, select

from app.core.db import engine
from app.models import TechStack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tech Stack seed data
TECH_STACK_DATA = [
    {
        "code": "nextjs",
        "name": "Next.js",
        "description": "Full-stack React framework với Server-Side Rendering, API Routes và App Router",
        "image": "/images/tech-stacks/nextjs.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "nextjs",
            "language": "typescript",
            "styling": "tailwindcss",
            "boilerplate_dir": "nextjs-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 1,
    },
    {
        "code": "react-vite",
        "name": "React + Vite",
        "description": "Single Page Application với React, Vite bundler và React Router",
        "image": "/images/tech-stacks/react.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "react",
            "bundler": "vite",
            "language": "typescript",
            "styling": "tailwindcss",
            "boilerplate_dir": "react-vite-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 2,
    },
    {
        "code": "nodejs-express",
        "name": "Node.js + Express",
        "description": "Backend API với Express.js, TypeScript và PostgreSQL",
        "image": "/images/tech-stacks/nodejs.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "express",
            "language": "typescript",
            "database": "postgresql",
            "orm": "prisma",
            "boilerplate_dir": "nodejs-express-boilerplate",
            "services": [
                {
                    "name": "api",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 3,
    },
    {
        "code": "python-fastapi",
        "name": "Python FastAPI",
        "description": "High-performance Python API với FastAPI, SQLAlchemy và PostgreSQL",
        "image": "/images/tech-stacks/fastapi.svg",
        "stack_config": {
            "runtime": "python",
            "package_manager": "pip",
            "framework": "fastapi",
            "language": "python",
            "database": "postgresql",
            "orm": "sqlalchemy",
            "boilerplate_dir": "python-fastapi-boilerplate",
            "services": [
                {
                    "name": "api",
                    "path": ".",
                    "format_cmd": "ruff format .",
                    "lint_fix_cmd": "ruff check --fix .",
                    "typecheck_cmd": "mypy .",
                    "build_cmd": "",
                    "dev_cmd": "uvicorn app.main:app --reload",
                    "test_cmd": "pytest",
                }
            ],
        },
        "display_order": 4,
    },
    {
        "code": "python-django",
        "name": "Python Django",
        "description": "Full-stack Python framework với Django, Django REST Framework và PostgreSQL",
        "image": "/images/tech-stacks/django.svg",
        "stack_config": {
            "runtime": "python",
            "package_manager": "pip",
            "framework": "django",
            "language": "python",
            "database": "postgresql",
            "orm": "django-orm",
            "boilerplate_dir": "python-django-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "ruff format .",
                    "lint_fix_cmd": "ruff check --fix .",
                    "typecheck_cmd": "mypy .",
                    "build_cmd": "python manage.py collectstatic --noinput",
                    "dev_cmd": "python manage.py runserver",
                    "test_cmd": "python manage.py test",
                }
            ],
        },
        "display_order": 5,
    },
    {
        "code": "fullstack-nextjs-fastapi",
        "name": "Next.js + FastAPI",
        "description": "Full-stack với Next.js frontend và FastAPI backend, tách biệt services",
        "image": "/images/tech-stacks/fullstack.svg",
        "stack_config": {
            "runtime": "mixed",
            "architecture": "monorepo",
            "boilerplate_dir": "fullstack-nextjs-fastapi-boilerplate",
            "services": [
                {
                    "name": "frontend",
                    "path": "frontend",
                    "runtime": "node",
                    "framework": "nextjs",
                    "language": "typescript",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                },
                {
                    "name": "backend",
                    "path": "backend",
                    "runtime": "python",
                    "framework": "fastapi",
                    "language": "python",
                    "format_cmd": "ruff format .",
                    "lint_fix_cmd": "ruff check --fix .",
                    "typecheck_cmd": "mypy .",
                    "build_cmd": "",
                    "dev_cmd": "uvicorn app.main:app --reload",
                    "test_cmd": "pytest",
                },
            ],
        },
        "display_order": 6,
    },
    {
        "code": "vue-nuxt",
        "name": "Nuxt.js (Vue)",
        "description": "Full-stack Vue framework với Server-Side Rendering và Auto-imports",
        "image": "/images/tech-stacks/nuxt.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "nuxt",
            "language": "typescript",
            "styling": "tailwindcss",
            "boilerplate_dir": "nuxt-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 7,
    },
    {
        "code": "angular",
        "name": "Angular",
        "description": "Enterprise-grade SPA framework với TypeScript và RxJS",
        "image": "/images/tech-stacks/angular.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "npm",
            "framework": "angular",
            "language": "typescript",
            "styling": "scss",
            "boilerplate_dir": "angular-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "npm run format",
                    "lint_fix_cmd": "ng lint --fix",
                    "typecheck_cmd": "npm run typecheck",
                    "build_cmd": "ng build",
                    "dev_cmd": "ng serve",
                    "test_cmd": "ng test",
                }
            ],
        },
        "display_order": 8,
    },
    {
        "code": "spring-boot",
        "name": "Spring Boot (Java)",
        "description": "Enterprise Java framework với Spring Boot, JPA và PostgreSQL",
        "image": "/images/tech-stacks/spring.svg",
        "stack_config": {
            "runtime": "java",
            "package_manager": "maven",
            "framework": "spring-boot",
            "language": "java",
            "database": "postgresql",
            "orm": "jpa",
            "boilerplate_dir": "spring-boot-boilerplate",
            "services": [
                {
                    "name": "api",
                    "path": ".",
                    "format_cmd": "mvn spotless:apply",
                    "lint_fix_cmd": "mvn checkstyle:check",
                    "typecheck_cmd": "mvn compile",
                    "build_cmd": "mvn package -DskipTests",
                    "dev_cmd": "mvn spring-boot:run",
                    "test_cmd": "mvn test",
                }
            ],
        },
        "display_order": 9,
    },
    {
        "code": "go-gin",
        "name": "Go + Gin",
        "description": "High-performance Go API với Gin framework và GORM",
        "image": "/images/tech-stacks/go.svg",
        "stack_config": {
            "runtime": "go",
            "package_manager": "go-modules",
            "framework": "gin",
            "language": "go",
            "database": "postgresql",
            "orm": "gorm",
            "boilerplate_dir": "go-gin-boilerplate",
            "services": [
                {
                    "name": "api",
                    "path": ".",
                    "format_cmd": "gofmt -w .",
                    "lint_fix_cmd": "golangci-lint run --fix",
                    "typecheck_cmd": "go vet ./...",
                    "build_cmd": "go build -o bin/server ./cmd/server",
                    "dev_cmd": "go run ./cmd/server",
                    "test_cmd": "go test ./...",
                }
            ],
        },
        "display_order": 10,
    },
    {
        "code": "rust-actix",
        "name": "Rust + Actix",
        "description": "Blazing-fast Rust API với Actix-web và Diesel ORM",
        "image": "/images/tech-stacks/rust.svg",
        "stack_config": {
            "runtime": "rust",
            "package_manager": "cargo",
            "framework": "actix-web",
            "language": "rust",
            "database": "postgresql",
            "orm": "diesel",
            "boilerplate_dir": "rust-actix-boilerplate",
            "services": [
                {
                    "name": "api",
                    "path": ".",
                    "format_cmd": "cargo fmt",
                    "lint_fix_cmd": "cargo clippy --fix",
                    "typecheck_cmd": "cargo check",
                    "build_cmd": "cargo build --release",
                    "dev_cmd": "cargo run",
                    "test_cmd": "cargo test",
                }
            ],
        },
        "display_order": 11,
    },
    {
        "code": "flutter",
        "name": "Flutter",
        "description": "Cross-platform mobile app với Flutter và Dart",
        "image": "/images/tech-stacks/flutter.svg",
        "stack_config": {
            "runtime": "dart",
            "package_manager": "pub",
            "framework": "flutter",
            "language": "dart",
            "platforms": ["ios", "android", "web"],
            "boilerplate_dir": "flutter-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "dart format .",
                    "lint_fix_cmd": "dart fix --apply",
                    "typecheck_cmd": "dart analyze",
                    "build_cmd": "flutter build apk",
                    "dev_cmd": "flutter run",
                    "test_cmd": "flutter test",
                }
            ],
        },
        "display_order": 12,
    },
    {
        "code": "react-native",
        "name": "React Native",
        "description": "Cross-platform mobile app với React Native và Expo",
        "image": "/images/tech-stacks/react-native.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "react-native",
            "language": "typescript",
            "platforms": ["ios", "android"],
            "expo": True,
            "boilerplate_dir": "react-native-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "eas build",
                    "dev_cmd": "expo start",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 13,
    },
    {
        "code": "electron",
        "name": "Electron",
        "description": "Desktop application với Electron, React và TypeScript",
        "image": "/images/tech-stacks/electron.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "electron",
            "language": "typescript",
            "ui_framework": "react",
            "platforms": ["windows", "macos", "linux"],
            "boilerplate_dir": "electron-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint:fix",
                    "typecheck_cmd": "pnpm run typecheck",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 14,
    },
    {
        "code": "svelte-kit",
        "name": "SvelteKit",
        "description": "Full-stack Svelte framework với SSR và file-based routing",
        "image": "/images/tech-stacks/svelte.svg",
        "stack_config": {
            "runtime": "node",
            "package_manager": "pnpm",
            "framework": "sveltekit",
            "language": "typescript",
            "styling": "tailwindcss",
            "boilerplate_dir": "sveltekit-boilerplate",
            "services": [
                {
                    "name": "app",
                    "path": ".",
                    "format_cmd": "pnpm run format",
                    "lint_fix_cmd": "pnpm run lint",
                    "typecheck_cmd": "pnpm run check",
                    "build_cmd": "pnpm run build",
                    "dev_cmd": "pnpm run dev",
                    "test_cmd": "pnpm run test",
                }
            ],
        },
        "display_order": 15,
    },
]


def seed_tech_stacks():
    """Seed tech stacks into database."""
    logger.info("Seeding tech stacks...")
    
    with Session(engine) as session:
        created_count = 0
        updated_count = 0
        
        for data in TECH_STACK_DATA:
            # Check if tech stack already exists
            existing = session.exec(
                select(TechStack).where(TechStack.code == data["code"])
            ).first()
            
            if existing:
                # Update existing
                for key, value in data.items():
                    setattr(existing, key, value)
                session.add(existing)
                updated_count += 1
                logger.info(f"  Updated: {data['code']} - {data['name']}")
            else:
                # Create new
                tech_stack = TechStack(**data)
                session.add(tech_stack)
                created_count += 1
                logger.info(f"  Created: {data['code']} - {data['name']}")
        
        session.commit()
        
    logger.info(f"Tech stacks seeding complete: {created_count} created, {updated_count} updated")
    return created_count, updated_count


def clear_tech_stacks():
    """Clear all tech stacks from database."""
    logger.info("Clearing tech stacks...")
    
    with Session(engine) as session:
        tech_stacks = session.exec(select(TechStack)).all()
        count = len(tech_stacks)
        
        for ts in tech_stacks:
            session.delete(ts)
        
        session.commit()
        
    logger.info(f"Cleared {count} tech stacks")
    return count


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_tech_stacks()
    else:
        seed_tech_stacks()
