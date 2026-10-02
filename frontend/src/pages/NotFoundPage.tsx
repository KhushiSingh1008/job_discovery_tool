import { Page } from "../components/layout/Page";
import { LinkButton } from "../components/ui/Button";
import { StateMessage } from "../components/ui/States";

export function NotFoundPage() {
  return (
    <Page title="Page not found">
      <StateMessage
        title="This page doesn't exist"
        action={
          <LinkButton to="/" variant="primary">
            Browse jobs
          </LinkButton>
        }
      >
        The link may be old or mistyped.
      </StateMessage>
    </Page>
  );
}
