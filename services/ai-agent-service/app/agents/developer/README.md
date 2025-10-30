- hiện tại developer của a có 2 mode là local và daytona muốn sang daytona
thì chỉnh DAYTONA_ENABLED=true ở .env
- ở test_developer_agent.py đổi path thư mục theo máy của e để chạy 
        result = agent.run(
                sprint_id="test-sprint-1",
                backlog_path=str(backlog_file),
                sprint_path=str(sprint_file),
                working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo", <-
                continue_on_error=True,
                github_repo_url="",
            )
- trong thư mục test demo , cd vào chạy :
1. git init
2. git add .
3. git commit - "abc"
4. git branch -m master main

- có một vài node ở implementor a không có dùng 