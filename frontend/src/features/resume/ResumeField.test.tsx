import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { jsonError, mockApi } from "../../test/mockApi";
import { renderWithProviders } from "../../test/render";
import { ResumeField } from "./ResumeField";

const TEXT = "Sam Lee\n- Responsible for handling cash on the till at a campus shop";

function setup(extract: () => unknown = () => ({ text: TEXT })) {
  const api = mockApi({ "POST /api/resume/extract": extract });
  const onChange = vi.fn();
  renderWithProviders(<ResumeField value="" onChange={onChange} />);
  return { ...api, onChange, user: userEvent.setup({ applyAccept: false }) };
}

const file = (name: string, size = 100) =>
  new File(["x".repeat(size)], name, { type: "application/octet-stream" });

describe("ResumeField", () => {
  it("sends an uploaded file as raw bytes and fills in its text", async () => {
    const { user, onChange, calls } = setup();
    const upload = file("resume.pdf");

    await user.upload(screen.getByLabelText("Upload resume file"), upload);

    expect(await screen.findByText(/Text loaded from resume.pdf/)).toBeInTheDocument();
    expect(onChange).toHaveBeenCalledWith(TEXT);
    const [call] = calls;
    expect(call?.body).toBe(upload); // the file itself, not a form
  });

  it("checks type and size before uploading anything", async () => {
    const { user, calls } = setup();

    await user.upload(screen.getByLabelText("Upload resume file"), file("photo.png"));
    expect(await screen.findByRole("alert")).toHaveTextContent("photo.png: Upload a PDF");

    await user.upload(screen.getByLabelText("Upload resume file"), file("cv.pdf", 2_100_000));
    expect(await screen.findByRole("alert")).toHaveTextContent("2 MB or smaller");
    expect(calls).toEqual([]);
  });

  it("shows the server's reason when a file can't be read", async () => {
    const { user, onChange } = setup(() => jsonError(422, "This PDF is password-protected."));

    await user.upload(screen.getByLabelText("Upload resume file"), file("locked.pdf"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "locked.pdf: This PDF is password-protected.",
    );
    expect(onChange).not.toHaveBeenCalled();
  });
});
