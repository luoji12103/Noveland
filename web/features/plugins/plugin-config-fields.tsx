"use client";

import type { PluginCatalogEntry } from "@/lib/worlds/types";

type PluginConfigFieldsProps = {
  plugins: PluginCatalogEntry[];
  selectedIdentifier: string;
  config: Record<string, unknown>;
  textareaId: string;
  textareaName: string;
};

type SchemaProperty = {
  name: string;
  type: "string" | "number" | "integer" | "boolean";
  title: string;
  description: string | null;
  required: boolean;
  value: unknown;
};

export function PluginConfigFields({
  plugins,
  selectedIdentifier,
  config,
  textareaId,
  textareaName,
}: PluginConfigFieldsProps) {
  const selectedPlugin = plugins.find((plugin) => plugin.identifier === selectedIdentifier) ?? null;
  const properties =
    selectedPlugin === null
      ? []
      : schemaProperties(selectedPlugin.config_schema, config);
  return (
    <fieldset className="schema-fieldset">
      <legend>Plugin config</legend>
      {selectedPlugin === null ? <p>Select a plugin to view schema fields.</p> : null}
      {selectedPlugin !== null && properties.length === 0 ? (
        <p>{selectedPlugin.identifier} does not expose configurable schema fields.</p>
      ) : null}
      {properties.map((property) => (
        <label className="field-label" key={property.name}>
          {property.title}
          {property.required ? " *" : ""}
          {property.type === "boolean" ? (
            <select
              className="text-input"
              data-plugin-config-field={property.name}
              defaultValue={property.value === true ? "true" : "false"}
            >
              <option value="false">false</option>
              <option value="true">true</option>
            </select>
          ) : (
            <input
              className="text-input"
              data-plugin-config-field={property.name}
              defaultValue={String(property.value ?? "")}
              inputMode={property.type === "number" || property.type === "integer" ? "decimal" : "text"}
            />
          )}
          {property.description !== null ? <span>{property.description}</span> : null}
        </label>
      ))}
      <label className="field-label">
        Raw JSON fallback
        <textarea
          className="text-input"
          id={textareaId}
          name={textareaName}
          rows={3}
          defaultValue={JSON.stringify(config, null, 2)}
        />
      </label>
    </fieldset>
  );
}

function schemaProperties(
  schema: Record<string, unknown>,
  config: Record<string, unknown>,
): SchemaProperty[] {
  const properties = schema.properties;
  if (!isRecord(properties)) {
    return [];
  }
  const requiredValues = schema.required;
  const required = new Set(
    Array.isArray(requiredValues) ? requiredValues.map((item) => String(item)) : [],
  );
  return Object.entries(properties).flatMap(([name, rawProperty]) => {
    if (!isRecord(rawProperty)) {
      return [];
    }
    const type = rawProperty.type;
    if (type !== "string" && type !== "number" && type !== "integer" && type !== "boolean") {
      return [];
    }
    return [
      {
        name,
        type,
        title: typeof rawProperty.title === "string" ? rawProperty.title : name,
        description:
          typeof rawProperty.description === "string" ? rawProperty.description : null,
        required: required.has(name),
        value: config[name],
      },
    ];
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
