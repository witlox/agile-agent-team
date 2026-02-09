# Rust Coding Standards

## Enforced by Tools

All Rust code MUST conform to these tool-enforced standards:

### 1. rustfmt (Official Formatter)
- **THE STANDARD** - All Rust code uses rustfmt
- **Line length**: 100 characters (default)
- **Indentation**: 4 spaces
- Run: `cargo fmt` (auto-formats entire codebase)
- Config in `rustfmt.toml` (minimal):
```toml
edition = "2021"
max_width = 100
```

### 2. clippy (Official Linter)
- **THE LINTER** - Catches common mistakes and suggests improvements
- Over 500+ lints for correctness, performance, style
- Run: `cargo clippy -- -D warnings` (treat warnings as errors)
- Default configuration is excellent, rarely needs changes

### 3. cargo check (Fast Type Checker)
- Checks code without building
- Run: `cargo check`
- Always passes before `cargo build`

### 4. cargo test (Testing)
- Test functions: `#[test]` attribute
- Integration tests in `tests/` directory
- Run: `cargo test`
- **Coverage requirement**: ≥85%
- For coverage: `cargo tarpaulin --out Html`

### 5. cargo doc (Documentation)
- Generated from `///` comments
- Run: `cargo doc --open`
- **All public items MUST be documented**

## Non-Negotiable Patterns

### Naming Conventions (Enforced by rustfmt/clippy)
```rust
// Types, Traits, Enums: PascalCase
struct UserAccount {}
trait Readable {}
enum Status { Active, Inactive }

// Functions, variables, modules: snake_case
fn get_user_by_id(id: i64) -> Result<User, Error> {}
let user_count = 42;
mod user_service;

// Constants: SCREAMING_SNAKE_CASE
const MAX_RETRIES: u32 = 3;
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);

// Type parameters: Single capital letter or PascalCase
fn process<T: Display>(item: T) {}
struct Container<Item> { items: Vec<Item> }

// Lifetimes: Short lowercase
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {}
```

### Error Handling (Required Pattern)
```rust
// ALWAYS use Result for fallible operations
fn get_user(id: i64) -> Result<User, UserError> {
    if id <= 0 {
        return Err(UserError::InvalidId);
    }

    let user = fetch_from_db(id)?;  // ? operator propagates errors
    Ok(user)
}

// Use thiserror for custom errors
use thiserror::Error;

#[derive(Error, Debug)]
pub enum UserError {
    #[error("User {0} not found")]
    NotFound(i64),

    #[error("Invalid user ID")]
    InvalidId,

    #[error("Database error")]
    Database(#[from] sqlx::Error),  // Auto-conversion
}

// Use anyhow for applications (not libraries)
use anyhow::{Context, Result};

fn process() -> Result<()> {
    let data = read_file("config.toml")
        .context("Failed to read config")?;
    Ok(())
}
```

### Ownership Rules (CORE RUST CONCEPT)
```rust
// Move semantics (ownership transfer)
fn take_ownership(s: String) {
    println!("{}", s);
}  // s is dropped here

// Borrowing (immutable reference)
fn borrow(s: &String) {
    println!("{}", s);
}  // s is NOT dropped, just borrowed

// Mutable borrowing
fn borrow_mut(s: &mut String) {
    s.push_str(" World");
}

// Use references unless you need ownership
fn process_users(users: &[User]) {  // Borrows slice
    for user in users {
        println!("{}", user.name);
    }
}
```

### Testing Pattern (Unit + Integration)
```rust
// Unit tests (same file)
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_user_creation() {
        let user = User::new("test@example.com".into());
        assert_eq!(user.email, "test@example.com");
    }

    #[test]
    fn test_invalid_email() {
        let result = User::new("invalid".into());
        assert!(result.is_err());
    }

    #[test]
    #[should_panic(expected = "Invalid ID")]
    fn test_panic_condition() {
        get_user(0);  // Should panic
    }
}

// Integration tests (tests/integration_test.rs)
use my_crate::UserService;

#[test]
fn test_user_workflow() {
    let service = UserService::new();
    let user = service.create_user("test@example.com").unwrap();
    let retrieved = service.get_user(user.id).unwrap();
    assert_eq!(retrieved.email, user.email);
}
```

### Documentation (rustdoc Format)
```rust
//! Module-level documentation.
//!
//! This module provides user management functionality.

/// Retrieves a user by their unique ID.
///
/// # Arguments
///
/// * `id` - The unique user identifier
///
/// # Returns
///
/// * `Ok(User)` - The user if found
/// * `Err(UserError::NotFound)` - If user doesn't exist
///
/// # Examples
///
/// ```
/// let user = get_user(123)?;
/// println!("Email: {}", user.email);
/// ```
///
/// # Errors
///
/// Returns `UserError::NotFound` if user doesn't exist.
pub fn get_user(id: i64) -> Result<User, UserError> {
    // Implementation
}
```

### Common Patterns (Idiomatic Rust)
```rust
// Use enums for state machines
enum OrderStatus {
    Pending,
    Processing { started_at: DateTime<Utc> },
    Completed { finished_at: DateTime<Utc> },
}

// Builder pattern
pub struct ConfigBuilder {
    host: String,
    port: u16,
}

impl ConfigBuilder {
    pub fn new(host: String) -> Self {
        Self { host, port: 8080 }
    }

    pub fn port(mut self, port: u16) -> Self {
        self.port = port;
        self
    }

    pub fn build(self) -> Config {
        Config { host: self.host, port: self.port }
    }
}

// Iterator chains (preferred over loops)
let total: i32 = numbers.iter()
    .filter(|&&x| x > 0)
    .map(|&x| x * 2)
    .sum();

// Match expressions (exhaustive)
match status {
    Status::Active => println!("Active"),
    Status::Inactive => println!("Inactive"),
    // Compiler ensures all variants handled
}
```

## Toolchain Commands

```bash
# Format code (ALWAYS run before commit)
cargo fmt

# Lint code (treat warnings as errors)
cargo clippy -- -D warnings

# Check code (fast, no build)
cargo check

# Run tests
cargo test

# Run tests with output
cargo test -- --nocapture

# All checks (CI pipeline)
cargo fmt -- --check && cargo clippy -- -D warnings && cargo test

# Build release
cargo build --release
```

## Rust Design Principles

These define idiomatic Rust (enforced by clippy):

1. **"Fearless concurrency"** - Ownership prevents data races at compile time
2. **"Zero-cost abstractions"** - High-level code compiles to efficient machine code
3. **"Explicit is better than implicit"** - No hidden control flow
4. **"Prefer composition over inheritance"** - Use traits and structs
5. **"Make illegal states unrepresentable"** - Use type system to enforce invariants

## Deviations Allowed Only For

1. **Line length**: Can exceed 100 chars for:
   - Long string literals
   - Complex type signatures

2. **Documentation**: Can skip for:
   - Private items in small modules
   - Obvious test helpers

3. **Error handling**: Can use `.unwrap()` only in:
   - Tests
   - Examples
   - After explicit checks that guarantee success

**All deviations MUST be justified with comments.**

## Common Mistakes to Avoid

```rust
// BAD: Using unwrap() in production
let user = get_user(id).unwrap();

// GOOD: Handle errors properly
let user = get_user(id)
    .context("Failed to retrieve user")?;

// BAD: Unnecessary cloning
let users_copy = users.clone();
process(users_copy);

// GOOD: Borrow instead
process(&users);

// BAD: Mutable variables when not needed
let mut count = 0;
count = calculate();

// GOOD: Immutable by default
let count = calculate();

// BAD: Using String when &str suffices
fn greet(name: &String) -> String {
    format!("Hello, {}", name)
}

// GOOD: Use &str for parameters
fn greet(name: &str) -> String {
    format!("Hello, {}", name)
}

// BAD: Ignoring Results
get_user(id);

// GOOD: Handle or explicitly discard
let _ = get_user(id).map_err(|e| eprintln!("Error: {}", e));
```

## Async/Await (Tokio Runtime)

```rust
use tokio;

#[tokio::main]
async fn main() -> Result<()> {
    let data = fetch_data("https://api.example.com").await?;
    println!("{}", data);
    Ok(())
}

async fn fetch_data(url: &str) -> Result<String> {
    let response = reqwest::get(url).await?;
    let text = response.text().await?;
    Ok(text)
}

// Concurrent operations
async fn fetch_all(urls: Vec<String>) -> Vec<Result<String>> {
    let futures = urls.iter().map(|url| fetch_data(url));
    futures::future::join_all(futures).await
}
```
