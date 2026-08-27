using System.Reflection;
using System.Text.Json;

if (args.Length != 2 || args[0] != "--output")
{
    Console.Error.WriteLine("Usage: dotnet run --project DotnetExceptionInventory.csproj -- --output <path>");
    return 2;
}

var runtimeDirectory = Path.GetDirectoryName(typeof(Exception).Assembly.Location)
    ?? throw new InvalidOperationException("Could not locate the active .NET runtime.");
var exceptionType = typeof(Exception);
var types = new SortedDictionary<string, Type>(StringComparer.Ordinal);

foreach (var assemblyPath in Directory.EnumerateFiles(runtimeDirectory, "*.dll"))
{
    try
    {
        var assembly = Assembly.Load(new AssemblyName(Path.GetFileNameWithoutExtension(assemblyPath)));
        foreach (var type in assembly.GetExportedTypes())
        {
            if (type.IsPublic && !type.ContainsGenericParameters && type != exceptionType && exceptionType.IsAssignableFrom(type) && type.FullName is { } fullName)
            {
                types.TryAdd(fullName, type);
            }
        }
    }
    catch (BadImageFormatException) { }
    catch (FileLoadException) { }
    catch (FileNotFoundException) { }
    catch (ReflectionTypeLoadException) { }
}

var runtimeVersion = Environment.Version.ToString();
var entries = types.Select(pair =>
{
    var fullName = pair.Key;
    var type = pair.Value;
    var category = fullName.StartsWith("System.IO.", StringComparison.Ordinal) ? "IO"
        : fullName.StartsWith("System.Net.", StringComparison.Ordinal) ? "Network"
        : fullName.StartsWith("System.Security.", StringComparison.Ordinal) ? "Security"
        : fullName.StartsWith("System.Threading.", StringComparison.Ordinal) ? "Concurrency"
        : fullName.Contains("Argument", StringComparison.Ordinal) || fullName.Contains("Format", StringComparison.Ordinal) ? "Type System"
        : "Runtime";
    var id = "dotnet_" + string.Concat(fullName.ToLowerInvariant().Select(character => char.IsLetterOrDigit(character) ? character : '_')).Trim('_');
    var sourceName = fullName.Replace('+', '.').ToLowerInvariant();
    return new
    {
        id,
        language = "C#",
        code = fullName,
        category,
        severity = "Runtime Exception",
        title = type.Name,
        description = $"Public .NET runtime exception type {fullName}, enumerated from the locally installed Microsoft.NETCore.App {runtimeVersion} shared runtime. Curated trigger context, reproduction, and remediation are pending editorial review.",
        bad_example = "// Registry-only record; a minimal reproduction is pending editorial review.",
        good_example = "// Registry-only record; a source-backed repair is pending editorial review.",
        version_introduced = $".NET {runtimeVersion}",
        version_deprecated = (string?)null,
        source_url = $"https://learn.microsoft.com/dotnet/api/{sourceName}",
        tier = 3,
        frequency = "Uncommon",
        situational_context = new[] { ".NET runtime", "public exception API" },
        interaction_types = new[] { "runtime" },
        related_errors = Array.Empty<string>(),
    };
}).ToArray();

var output = Path.GetFullPath(args[1]);
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
await File.WriteAllTextAsync(output, JsonSerializer.Serialize(entries, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine);
Console.WriteLine($"Extracted {entries.Length} public .NET runtime exception types from {runtimeDirectory}.");
return 0;
