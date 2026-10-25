//! Test-only desktop transport for Python integration tests. Each input line
//! calls the same Rust function as JNI; stdout contains only JSON responses.
use std::io::{self, BufRead, Write};

pub fn run() -> io::Result<()> {
    let result = serve(io::stdin().lock(), io::stdout().lock());
    // Closing stdin (including after a failed Python test) releases the session.
    let cleanup = super::runtime().block_on(super::close_session(None));
    result?;
    cleanup.map_err(io::Error::other)?;
    Ok(())
}

fn serve(mut input: impl BufRead, mut output: impl Write) -> io::Result<()> {
    let mut request = Vec::new();
    loop {
        request.clear();
        if input.read_until(b'\n', &mut request)? == 0 {
            return Ok(());
        }
        writeln!(output, "{}", super::call_json(&request))?;
        output.flush()?;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{from_str, json, Value};

    #[test]
    fn consecutive_requests_preserve_unicode_and_recover_from_invalid_json() {
        let mut output = Vec::new();
        serve(
            &b"invalid json\n{\"op\":\"\xe8\x8d\x89\xf0\x9f\x8c\xb1\"}\n{\"op\":\"unsubscribe\",\"subscription_id\":\"missing\"}"[..],
            &mut output,
        )
        .unwrap();
        let responses: Vec<Value> = String::from_utf8(output)
            .unwrap()
            .lines()
            .map(|line| from_str(line).unwrap())
            .collect();
        assert_eq!(responses.len(), 3);
        assert_eq!(responses[0]["ok"], false);
        assert!(responses[1]["error"].as_str().unwrap().contains("草🌱"));
        assert_eq!(responses[2], json!({"ok":true,"result":null}));
    }
}
