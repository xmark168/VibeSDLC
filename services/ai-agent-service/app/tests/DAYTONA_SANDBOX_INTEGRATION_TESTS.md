# 📋 DAYTONA SANDBOX MANAGEMENT - INTEGRATION TEST CASES

## 📊 DAYTONA ARCHITECTURE

### Daytona Integration Components

```
Daytona Sandbox Integration
├── DaytonaConfig (Configuration)
│   ├── api_key: Daytona API key
│   ├── api_url: Daytona API URL
│   ├── organization_id: Organization ID
│   ├── target: Region (us, eu)
│   ├── enabled: Enable/disable flag
│   ├── sandbox_language: Language (node, python)
│   ├── sandbox_snapshot: Snapshot name
│   └── workspace_path: /root/workspace
├── SandboxManager (Lifecycle Management)
│   ├── create_sandbox(): Create new sandbox
│   ├── get_sandbox(): Get sandbox instance
│   ├── is_sandbox_active(): Check if active
│   ├── get_workspace_path(): Get workspace path
│   └── cleanup_sandbox(): Delete sandbox
├── FilesystemAdapter (Abstraction Layer)
│   ├── LocalFilesystemAdapter: Local filesystem
│   └── DaytonaFilesystemAdapter: Sandbox filesystem
└── GitAdapter (Abstraction Layer)
    ├── LocalGitAdapter: Local git
    └── DaytonaGitAdapter: Sandbox git
```

### Adapter Pattern

| Component | Local Mode | Daytona Mode |
|---|---|---|
| **Filesystem** | LocalFilesystemAdapter | DaytonaFilesystemAdapter |
| **Git** | LocalGitAdapter | DaytonaGitAdapter |
| **Configuration** | DAYTONA_ENABLED=false | DAYTONA_ENABLED=true |
| **Execution** | Local machine | Remote sandbox |

---

## 🧪 INTEGRATION TEST CASES

### GROUP 1: DAYTONA CONFIGURATION

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-01** | Load Daytona Config from Env | 1. Read DAYTONA_ENABLED<br>2. Read API credentials<br>3. Parse config<br>4. Return config object | ✅ Config loaded<br>✅ api_key set<br>✅ api_url set<br>✅ organization_id set | DAYTONA_ENABLED=true<br>All env vars set |
| **TC-DS-02** | Validate Daytona Config | 1. Load config<br>2. Validate required fields<br>3. Check API URL format<br>4. Report validation result | ✅ Config valid<br>✅ All fields present<br>✅ URL format correct<br>✅ Validation passed | Config loaded |
| **TC-DS-03** | Handle Missing Config | 1. Try to load config<br>2. Check for missing fields<br>3. Return error<br>4. Fallback to local mode | ✅ Missing fields detected<br>✅ Error logged<br>✅ Fallback to local<br>✅ Graceful handling | DAYTONA_ENABLED=true<br>Missing env vars |
| **TC-DS-04** | Disable Daytona Mode | 1. Set DAYTONA_ENABLED=false<br>2. Load config<br>3. Check enabled flag<br>4. Return None | ✅ Config returns None<br>✅ Local mode active<br>✅ No Daytona SDK loaded<br>✅ Backward compatible | DAYTONA_ENABLED=false |

### GROUP 2: SANDBOX LIFECYCLE MANAGEMENT

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-05** | Create Sandbox | 1. Initialize SandboxManager<br>2. Call create_sandbox()<br>3. Wait for creation<br>4. Return sandbox_id | ✅ Sandbox created<br>✅ sandbox_id returned<br>✅ Status = "created"<br>✅ Workspace path set | Config loaded<br>Daytona API available |
| **TC-DS-06** | Check Sandbox Active | 1. Create sandbox<br>2. Call is_sandbox_active()<br>3. Check status<br>4. Return boolean | ✅ Sandbox active<br>✅ is_sandbox_active() = true<br>✅ Status verified<br>✅ Check successful | Sandbox created |
| **TC-DS-07** | Get Sandbox Instance | 1. Create sandbox<br>2. Call get_sandbox()<br>3. Return sandbox object<br>4. Verify object | ✅ Sandbox object returned<br>✅ Object has fs API<br>✅ Object has git API<br>✅ Object valid | Sandbox created |
| **TC-DS-08** | Cleanup Sandbox | 1. Create sandbox<br>2. Call cleanup_sandbox()<br>3. Wait for deletion<br>4. Return status | ✅ Sandbox deleted<br>✅ Status = "deleted"<br>✅ sandbox_id returned<br>✅ Cleanup successful | Sandbox created |

### GROUP 3: SANDBOX WORKSPACE MANAGEMENT

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-09** | Get Workspace Path | 1. Create sandbox<br>2. Call get_workspace_path("repo")<br>3. Return path<br>4. Verify path format | ✅ Path returned<br>✅ Path = "/root/workspace/repo"<br>✅ Format correct<br>✅ Path valid | Sandbox created |
| **TC-DS-10** | Create Workspace Directory | 1. Create sandbox<br>2. Create directory in workspace<br>3. Verify creation<br>4. Return status | ✅ Directory created<br>✅ Path exists in sandbox<br>✅ Status = "success"<br>✅ Creation successful | Sandbox created |
| **TC-DS-11** | List Workspace Files | 1. Create sandbox<br>2. Upload test files<br>3. List files<br>4. Return file list | ✅ Files listed<br>✅ File count correct<br>✅ File names returned<br>✅ List successful | Sandbox created<br>Files uploaded |
| **TC-DS-12** | Get Workspace Info | 1. Create sandbox<br>2. Get workspace info<br>3. Return metadata<br>4. Verify info | ✅ Info returned<br>✅ Total size shown<br>✅ File count shown<br>✅ Info valid | Sandbox created |

### GROUP 4: FILESYSTEM ADAPTER - LOCAL MODE

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-13** | Get Local Filesystem Adapter | 1. Set DAYTONA_ENABLED=false<br>2. Call get_filesystem_adapter()<br>3. Check adapter type<br>4. Return adapter | ✅ LocalFilesystemAdapter returned<br>✅ Type correct<br>✅ Adapter ready<br>✅ No Daytona SDK | DAYTONA_ENABLED=false |
| **TC-DS-14** | Read File (Local Mode) | 1. Get local adapter<br>2. Create test file<br>3. Call read_file()<br>4. Return content | ✅ File read<br>✅ Content correct<br>✅ Line numbers shown<br>✅ Read successful | Local adapter ready<br>Test file exists |
| **TC-DS-15** | Write File (Local Mode) | 1. Get local adapter<br>2. Call write_file()<br>3. Verify file created<br>4. Return status | ✅ File written<br>✅ Content saved<br>✅ Status = "success"<br>✅ Write successful | Local adapter ready |
| **TC-DS-16** | List Files (Local Mode) | 1. Get local adapter<br>2. Create test files<br>3. Call list_files()<br>4. Return file list | ✅ Files listed<br>✅ File count correct<br>✅ File names returned<br>✅ List successful | Local adapter ready<br>Test files exist |

### GROUP 5: FILESYSTEM ADAPTER - DAYTONA MODE

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-17** | Get Daytona Filesystem Adapter | 1. Set DAYTONA_ENABLED=true<br>2. Create sandbox<br>3. Call get_filesystem_adapter()<br>4. Return adapter | ✅ DaytonaFilesystemAdapter returned<br>✅ Type correct<br>✅ Adapter ready<br>✅ Sandbox linked | DAYTONA_ENABLED=true<br>Sandbox created |
| **TC-DS-18** | Read File (Daytona Mode) | 1. Get Daytona adapter<br>2. Upload test file<br>3. Call read_file()<br>4. Return content | ✅ File read from sandbox<br>✅ Content correct<br>✅ Line numbers shown<br>✅ Read successful | Daytona adapter ready<br>File uploaded |
| **TC-DS-19** | Write File (Daytona Mode) | 1. Get Daytona adapter<br>2. Call write_file()<br>3. Verify in sandbox<br>4. Return status | ✅ File written to sandbox<br>✅ Content saved<br>✅ Status = "success"<br>✅ Write successful | Daytona adapter ready |
| **TC-DS-20** | List Files (Daytona Mode) | 1. Get Daytona adapter<br>2. Upload test files<br>3. Call list_files()<br>4. Return file list | ✅ Files listed from sandbox<br>✅ File count correct<br>✅ File names returned<br>✅ List successful | Daytona adapter ready<br>Files uploaded |

### GROUP 6: GIT ADAPTER - LOCAL MODE

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-21** | Get Local Git Adapter | 1. Set DAYTONA_ENABLED=false<br>2. Call get_git_adapter()<br>3. Check adapter type<br>4. Return adapter | ✅ LocalGitAdapter returned<br>✅ Type correct<br>✅ Adapter ready<br>✅ No Daytona SDK | DAYTONA_ENABLED=false |
| **TC-DS-22** | Clone Repository (Local Mode) | 1. Get local git adapter<br>2. Call clone()<br>3. Verify repo cloned<br>4. Return status | ✅ Repo cloned<br>✅ Status = "success"<br>✅ Path correct<br>✅ Clone successful | Local git adapter ready |
| **TC-DS-23** | Create Branch (Local Mode) | 1. Get local git adapter<br>2. Call create_branch()<br>3. Verify branch created<br>4. Return status | ✅ Branch created<br>✅ Status = "success"<br>✅ Branch name correct<br>✅ Creation successful | Local git adapter ready<br>Repo cloned |
| **TC-DS-24** | Commit Changes (Local Mode) | 1. Get local git adapter<br>2. Make changes<br>3. Call commit()<br>4. Return commit hash | ✅ Commit created<br>✅ Status = "success"<br>✅ Commit hash returned<br>✅ Commit successful | Local git adapter ready<br>Repo cloned |

### GROUP 7: GIT ADAPTER - DAYTONA MODE

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-25** | Get Daytona Git Adapter | 1. Set DAYTONA_ENABLED=true<br>2. Create sandbox<br>3. Call get_git_adapter()<br>4. Return adapter | ✅ DaytonaGitAdapter returned<br>✅ Type correct<br>✅ Adapter ready<br>✅ Sandbox linked | DAYTONA_ENABLED=true<br>Sandbox created |
| **TC-DS-26** | Clone Repository (Daytona Mode) | 1. Get Daytona git adapter<br>2. Call clone()<br>3. Verify in sandbox<br>4. Return status | ✅ Repo cloned in sandbox<br>✅ Status = "success"<br>✅ Path correct<br>✅ Clone successful | Daytona git adapter ready |
| **TC-DS-27** | Create Branch (Daytona Mode) | 1. Get Daytona git adapter<br>2. Call create_branch()<br>3. Verify in sandbox<br>4. Return status | ✅ Branch created in sandbox<br>✅ Status = "success"<br>✅ Branch name correct<br>✅ Creation successful | Daytona git adapter ready<br>Repo cloned |
| **TC-DS-28** | Commit Changes (Daytona Mode) | 1. Get Daytona git adapter<br>2. Make changes<br>3. Call commit()<br>4. Return commit hash | ✅ Commit in sandbox<br>✅ Status = "success"<br>✅ Commit hash returned<br>✅ Commit successful | Daytona git adapter ready<br>Repo cloned |

### GROUP 8: BACKWARD COMPATIBILITY

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-29** | Local Mode Backward Compatibility | 1. Set DAYTONA_ENABLED=false<br>2. Get adapters<br>3. Verify local adapters<br>4. Test operations | ✅ Local adapters returned<br>✅ No Daytona SDK loaded<br>✅ Operations work<br>✅ Backward compatible | DAYTONA_ENABLED=false |
| **TC-DS-30** | Adapter Factory Fallback | 1. Enable Daytona<br>2. No active sandbox<br>3. Call get_adapters()<br>4. Fallback to local | ✅ Fallback triggered<br>✅ Local adapters returned<br>✅ Warning logged<br>✅ Graceful fallback | DAYTONA_ENABLED=true<br>No sandbox |
| **TC-DS-31** | Mixed Mode Operations | 1. Start in local mode<br>2. Switch to Daytona<br>3. Verify adapter switch<br>4. Test operations | ✅ Adapters switched<br>✅ Operations work<br>✅ No conflicts<br>✅ Switch successful | Both modes available |
| **TC-DS-32** | Sandbox Manager Singleton | 1. Create SandboxManager<br>2. Get instance again<br>3. Verify same instance<br>4. Check state | ✅ Same instance returned<br>✅ State preserved<br>✅ Singleton pattern<br>✅ Verification passed | SandboxManager initialized |

### GROUP 9: ERROR HANDLING & RECOVERY

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-33** | Handle Sandbox Creation Failure | 1. Mock API failure<br>2. Call create_sandbox()<br>3. Catch exception<br>4. Return error | ✅ Exception caught<br>✅ Error logged<br>✅ Error message clear<br>✅ Graceful failure | Daytona API unavailable |
| **TC-DS-34** | Handle Sandbox Cleanup Failure | 1. Create sandbox<br>2. Mock cleanup failure<br>3. Call cleanup_sandbox()<br>4. Return error | ✅ Exception caught<br>✅ Error logged<br>✅ Error message clear<br>✅ Graceful failure | Sandbox created<br>API failure |
| **TC-DS-35** | Handle File Operation Failure | 1. Get adapter<br>2. Mock file operation failure<br>3. Call read_file()<br>4. Return error | ✅ Exception caught<br>✅ Error logged<br>✅ Error message clear<br>✅ Graceful failure | Adapter ready<br>File not found |
| **TC-DS-36** | Handle Git Operation Failure | 1. Get git adapter<br>2. Mock git failure<br>3. Call clone()<br>4. Return error | ✅ Exception caught<br>✅ Error logged<br>✅ Error message clear<br>✅ Graceful failure | Git adapter ready<br>Invalid repo URL |

### GROUP 10: INTEGRATION WITH DEVELOPER AGENT

| TC ID | Description | Agent Steps | Expected Results | Pre-conditions |
|---|---|---|---|---|
| **TC-DS-37** | Developer Agent Local Mode | 1. Set DAYTONA_ENABLED=false<br>2. Run Developer Agent<br>3. Verify local operations<br>4. Check results | ✅ Agent runs locally<br>✅ All operations local<br>✅ Results correct<br>✅ Execution successful | DAYTONA_ENABLED=false |
| **TC-DS-38** | Developer Agent Daytona Mode | 1. Set DAYTONA_ENABLED=true<br>2. Create sandbox<br>3. Run Developer Agent<br>4. Check results | ✅ Agent runs in sandbox<br>✅ All operations in sandbox<br>✅ Results correct<br>✅ Execution successful | DAYTONA_ENABLED=true<br>Sandbox created |
| **TC-DS-39** | Developer Agent Sandbox Reuse | 1. Create sandbox<br>2. Run task 1<br>3. Run task 2<br>4. Verify reuse | ✅ Sandbox reused<br>✅ Same sandbox_id<br>✅ Both tasks complete<br>✅ Reuse successful | Sandbox created |
| **TC-DS-40** | Developer Agent Sandbox Cleanup | 1. Create sandbox<br>2. Run tasks<br>3. Call cleanup<br>4. Verify deleted | ✅ Sandbox deleted<br>✅ Status = "deleted"<br>✅ Cleanup successful<br>✅ Resources freed | Sandbox created<br>Tasks completed |

---

## 📊 TEST SUMMARY

| Category | Count | Status |
|---|---|---|
| **Daytona Configuration** | 4 | ✅ Ready |
| **Sandbox Lifecycle Management** | 4 | ✅ Ready |
| **Sandbox Workspace Management** | 4 | ✅ Ready |
| **Filesystem Adapter - Local Mode** | 4 | ✅ Ready |
| **Filesystem Adapter - Daytona Mode** | 4 | ✅ Ready |
| **Git Adapter - Local Mode** | 4 | ✅ Ready |
| **Git Adapter - Daytona Mode** | 4 | ✅ Ready |
| **Backward Compatibility** | 4 | ✅ Ready |
| **Error Handling & Recovery** | 4 | ✅ Ready |
| **Integration with Developer Agent** | 4 | ✅ Ready |
| **TOTAL** | **40 Test Cases** | ✅ Ready |

---

## 🎯 IMPLEMENTATION PRIORITY

### Phase 1: Foundation (Critical)
- TC-DS-01 to TC-DS-04: Configuration
- TC-DS-05 to TC-DS-08: Sandbox Lifecycle
- TC-DS-09 to TC-DS-12: Workspace Management

### Phase 2: Adapter Implementation (High)
- TC-DS-13 to TC-DS-16: Filesystem Local
- TC-DS-17 to TC-DS-20: Filesystem Daytona
- TC-DS-21 to TC-DS-24: Git Local

### Phase 3: Daytona Integration (High)
- TC-DS-25 to TC-DS-28: Git Daytona
- TC-DS-29 to TC-DS-32: Backward Compatibility
- TC-DS-33 to TC-DS-36: Error Handling

### Phase 4: Full Integration (Medium)
- TC-DS-37 to TC-DS-40: Developer Agent Integration

